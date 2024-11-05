from unittest.mock import AsyncMock, Mock

import pytest
from httpx import AsyncClient, Response
from meldingen_core.image import BaseImageOptimizer
from plugfs.filesystem import Filesystem

from meldingen.image import (
    ImageOptimizerException,
    ImageOptimizerTask,
    IMGProxyImageOptimizer,
    IMGProxyImageOptimizerUrlGenerator,
    IMGProxySignatureGenerator,
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

    url = generate_url("https://images/path/to/image.jpg")

    assert (
        url
        == "http://imgproxy/oKfUtW34Dvo2BGQehJFR4Nr0_rIjOtdtzJ3QFsUcXH8/f:webp/plain/https://images/path/to/image.jpg"
    )


@pytest.mark.anyio
async def test_imgproxy_image_optimizer() -> None:
    url_generator = Mock(IMGProxyImageOptimizerUrlGenerator)
    url_generator.return_value = "http://some.url"

    filesystem = Mock(Filesystem)

    response = Mock(Response)
    response.status_code = 200

    http_client = AsyncMock(AsyncClient)
    http_client.stream.return_value.__aenter__.return_value = response
    optimize = IMGProxyImageOptimizer(url_generator, filesystem, http_client)

    optimized_url = await optimize("/path/to/image.jpg")

    http_client.stream.assert_called_with("GET", "http://some.url")
    filesystem.write_iterator.assert_awaited_once()
    assert optimized_url == "/path/to/image-optimized.webp"


@pytest.mark.anyio
async def test_imgproxy_image_optimizer_request_failed() -> None:
    response = Mock(Response)
    response.status_code = 404

    http_client = AsyncMock(AsyncClient)
    http_client.stream.return_value.__aenter__.return_value = response

    optimize = IMGProxyImageOptimizer(Mock(IMGProxyImageOptimizerUrlGenerator), Mock(Filesystem), http_client)

    with pytest.raises(ImageOptimizerException):
        await optimize("/path/to/image.jpg")


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
