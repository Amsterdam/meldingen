from unittest.mock import AsyncMock, Mock

import pytest
from httpx import AsyncClient, Response
from meldingen_core.image import BaseImageOptimizer, BaseThumbnailGenerator
from plugfs.filesystem import Filesystem

from meldingen.image import (
    ImageOptimizerException,
    ImageOptimizerTask,
    IMGProxyImageOptimizer,
    IMGProxyImageOptimizerUrlGenerator,
    IMGProxyImageProcessor,
    IMGProxySignatureGenerator,
    IMGProxyThumbnailGenerator,
    IMGProxyThumbnailUrlGenerator,
    ThumbnailGeneratorTask,
)
from meldingen.models import Attachment, Melding
from meldingen.repositories import AttachmentRepository


def test_imgproxy_signature_generator() -> None:
    """Based on the example @ https://docs.imgproxy.net/usage/signing_url"""
    generate_signature = IMGProxySignatureGenerator("736563726574", "68656C6C6F")

    signature = generate_signature(
        "/rs:fill:300:400:0/g:sm/aHR0cDovL2V4YW1w/bGUuY29tL2ltYWdl/cy9jdXJpb3NpdHku/anBn.png"
    )

    assert signature == "oKfUtW34Dvo2BGQehJFR4Nr0_rIjOtdtzJ3QFsUcXH8"


def test_imgproxy_image_optimizer_url_generator() -> None:
    signature_generator = Mock(IMGProxySignatureGenerator)
    signature_generator.return_value = "oKfUtW34Dvo2BGQehJFR4Nr0_rIjOtdtzJ3QFsUcXH8"

    generate_url = IMGProxyImageOptimizerUrlGenerator(signature_generator, "http://imgproxy")

    url = generate_url("path/to/image.jpg")

    assert url == "http://imgproxy/oKfUtW34Dvo2BGQehJFR4Nr0_rIjOtdtzJ3QFsUcXH8/f:webp/plain/path/to/image.jpg"


def test_imgproxy_thumbnail_url_generator() -> None:
    signature_generator = Mock(IMGProxySignatureGenerator)
    signature_generator.return_value = "oKfUtW34Dvo2BGQehJFR4Nr0_rIjOtdtzJ3QFsUcXH8"

    generate_url = IMGProxyThumbnailUrlGenerator(signature_generator, "http://imgproxy", 150, 150)

    url = generate_url("path/to/image.jpg")

    assert (
        url
        == "http://imgproxy/oKfUtW34Dvo2BGQehJFR4Nr0_rIjOtdtzJ3QFsUcXH8/rs:auto:150:150/f:webp/plain/path/to/image.jpg"
    )


@pytest.mark.anyio
async def test_imgproxy_image_processor() -> None:
    url_generator = Mock(IMGProxyImageOptimizerUrlGenerator)
    url_generator.return_value = "http://some.url"

    filesystem = Mock(Filesystem)

    response = Mock(Response)
    response.status_code = 200

    http_client = AsyncMock(AsyncClient)
    http_client.stream.return_value.__aenter__.return_value = response
    process = IMGProxyImageProcessor(url_generator, http_client, filesystem)

    processed_path = await process("path/to/image.jpg", "processed")

    http_client.stream.assert_called_with("GET", "http://some.url")
    filesystem.write_iterator.assert_awaited_once()
    assert processed_path == "path/to/image-processed.webp"


@pytest.mark.anyio
async def test_imgproxy_image_processor_request_failed() -> None:
    response = Mock(Response)
    response.status_code = 404

    http_client = AsyncMock(AsyncClient)
    http_client.stream.return_value.__aenter__.return_value = response

    process = IMGProxyImageProcessor(Mock(IMGProxyImageOptimizerUrlGenerator), http_client, Mock(Filesystem))

    with pytest.raises(ImageOptimizerException):
        await process("/path/to/image.jpg", "processed")


@pytest.mark.anyio
async def test_imgproxy_image_optimizer() -> None:
    expected_path = "path/to/image-optimized.webp"
    processor = AsyncMock(IMGProxyImageProcessor, return_value=expected_path)
    optimize = IMGProxyImageOptimizer(processor)
    path = "path/to/image.jpg"

    optimized_path = await optimize(path)

    assert optimized_path == expected_path
    # For some reason assert_awaited_once_with() does not work, so we go through the hassle below
    assert len(processor.mock_calls) == 1
    _, args, _ = processor.mock_calls[0]
    assert len(args) == 2
    assert args[0] == path
    assert args[1] == "optimized"


@pytest.mark.anyio
async def test_imgproxy_thumbnail_generator() -> None:
    expected_path = "path/to/image-thumbnail.webp"
    processor = AsyncMock(IMGProxyImageProcessor, return_value=expected_path)
    optimize = IMGProxyThumbnailGenerator(processor)
    path = "path/to/image.jpg"

    thumbnail_path = await optimize(path)

    assert thumbnail_path == expected_path
    # For some reason assert_awaited_once_with() does not work, so we go through the hassle below
    assert len(processor.mock_calls) == 1
    _, args, _ = processor.mock_calls[0]
    assert len(args) == 2
    assert args[0] == path
    assert args[1] == "thumbnail"


@pytest.mark.anyio
async def test_image_optimizer_task() -> None:
    attachment = Attachment(original_filename="image.jpg", melding=Mock(Melding))
    attachment.file_path = "/path/to/image.jpg"

    optimized_path = "/path/to/image-optimized.webp"
    optimizer = AsyncMock(BaseImageOptimizer, return_value=optimized_path)
    repository = Mock(AttachmentRepository)

    run = ImageOptimizerTask(optimizer, repository)

    await run(attachment)

    assert attachment.optimized_path == optimized_path
    repository.save.assert_awaited_once_with(attachment)


@pytest.mark.anyio
async def test_thumbnail_generator_task() -> None:
    attachment = Attachment(original_filename="image.jpg", melding=Mock(Melding))
    attachment.file_path = "path/to/image.jpg"

    thumbnail_path = "path/to/image-thumbnail.webp"
    thumbnail_generator = AsyncMock(BaseThumbnailGenerator, return_value=thumbnail_path)
    repository = Mock(AttachmentRepository)

    run = ThumbnailGeneratorTask(thumbnail_generator, repository)

    await run(attachment)

    assert attachment.thumbnail_path == thumbnail_path
    repository.save.assert_awaited_once_with(attachment)
