from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import BackgroundTasks
from httpx import AsyncClient, Response
from meldingen_core.image import BaseImageOptimizer, BaseThumbnailGenerator
from meldingen_core.malware import BaseMalwareScanner
from plugfs.filesystem import Filesystem

from meldingen.factories import BaseFilesystemFactory
from meldingen.image import (
    BaseMetadataStripper,
    ImageOptimizerException,
    ImageOptimizerTask,
    IMGProxyImageOptimizer,
    IMGProxyImageOptimizerUrlGenerator,
    IMGProxyImageProcessor,
    IMGProxyMetadataStripper,
    IMGProxyMetadataStripUrlGenerator,
    IMGProxySignatureGenerator,
    IMGProxyThumbnailGenerator,
    IMGProxyThumbnailUrlGenerator,
    Ingestor,
    MetadataStripperException,
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

    assert url == (
        "http://imgproxy/oKfUtW34Dvo2BGQehJFR4Nr0_rIjOtdtzJ3QFsUcXH8/sm:1/kcr:0/f:webp/plain/path/to/image.jpg"
    )


def test_imgproxy_thumbnail_url_generator() -> None:
    signature_generator = Mock(IMGProxySignatureGenerator)
    signature_generator.return_value = "oKfUtW34Dvo2BGQehJFR4Nr0_rIjOtdtzJ3QFsUcXH8"

    generate_url = IMGProxyThumbnailUrlGenerator(signature_generator, "http://imgproxy", 150, 150)

    url = generate_url("path/to/image.jpg")

    assert url == (
        "http://imgproxy/oKfUtW34Dvo2BGQehJFR4Nr0_rIjOtdtzJ3QFsUcXH8"
        "/sm:1/kcr:0/rs:fit:150:150/f:webp/plain/path/to/image.jpg"
    )


def test_imgproxy_metadata_strip_url_generator() -> None:
    signature_generator = Mock(IMGProxySignatureGenerator)
    signature_generator.return_value = "oKfUtW34Dvo2BGQehJFR4Nr0_rIjOtdtzJ3QFsUcXH8"

    generate_url = IMGProxyMetadataStripUrlGenerator(signature_generator, "http://imgproxy", 90)

    url = generate_url("path/to/image.jpg")

    # No format option, so imgproxy returns the image in its source format
    assert url == "http://imgproxy/oKfUtW34Dvo2BGQehJFR4Nr0_rIjOtdtzJ3QFsUcXH8/sm:1/kcr:0/q:90/plain/path/to/image.jpg"


@pytest.mark.anyio
async def test_imgproxy_image_processor() -> None:
    filesystem = Mock(Filesystem)

    class AIterator(AsyncIterator[Filesystem]):
        _round: int = 0

        def __aiter__(self) -> AsyncIterator[Filesystem]:
            return self

        async def __anext__(self) -> Filesystem:
            if self._round == 0:
                self._round += 1
                return filesystem

            raise StopAsyncIteration

    url_generator = Mock(IMGProxyImageOptimizerUrlGenerator)
    url_generator.return_value = "http://some.url"

    response = Mock(Response)
    response.status_code = 200

    http_client = AsyncMock(AsyncClient)
    http_client.stream.return_value.__aenter__.return_value = response

    filesystem_factory = Mock(BaseFilesystemFactory)
    filesystem_factory.return_value = AIterator()

    process = IMGProxyImageProcessor(url_generator, http_client, filesystem_factory)

    processed_path, media_type = await process("path/to/image.jpg", "processed")

    http_client.stream.assert_called_with("GET", "http://some.url")
    filesystem.write_iterator.assert_awaited_once()
    assert processed_path == "path/to/image-processed.webp"
    assert media_type == "image/webp"


@pytest.mark.anyio
async def test_imgproxy_image_processor_request_failed() -> None:
    filesystem = Mock(Filesystem)

    class AIterator(AsyncIterator[Filesystem]):
        _round: int = 0

        def __aiter__(self) -> AsyncIterator[Filesystem]:
            return self

        async def __anext__(self) -> Filesystem:
            if self._round == 0:
                self._round += 1
                return filesystem

            raise StopAsyncIteration

    response = Mock(Response)
    response.status_code = 404

    http_client = AsyncMock(AsyncClient)
    http_client.stream.return_value.__aenter__.return_value = response

    filesystem_factory = Mock(BaseFilesystemFactory)
    filesystem_factory.return_value = AIterator()

    process = IMGProxyImageProcessor(Mock(IMGProxyImageOptimizerUrlGenerator), http_client, filesystem_factory)

    with pytest.raises(ImageOptimizerException):
        await process("/path/to/image.jpg", "processed")


@pytest.mark.anyio
async def test_imgproxy_metadata_stripper() -> None:
    filesystem = AsyncMock(Filesystem)

    class AIterator(AsyncIterator[Filesystem]):
        _round: int = 0

        def __aiter__(self) -> AsyncIterator[Filesystem]:
            return self

        async def __anext__(self) -> Filesystem:
            if self._round == 0:
                self._round += 1
                return filesystem

            raise StopAsyncIteration

    url_generator = Mock(IMGProxyMetadataStripUrlGenerator)
    url_generator.return_value = "http://some.url"

    response = Mock(Response)
    response.status_code = 200
    response.content = b"stripped image"

    http_client = AsyncMock(AsyncClient)
    http_client.get.return_value = response

    filesystem_factory = Mock(BaseFilesystemFactory)
    filesystem_factory.return_value = AIterator()

    strip_metadata = IMGProxyMetadataStripper(url_generator, http_client, filesystem_factory)

    await strip_metadata("path/to/image.jpg")

    http_client.get.assert_awaited_once_with("http://some.url")
    # The metadata free image replaces the original
    filesystem.write.assert_awaited_once_with("path/to/image.jpg", b"stripped image")


@pytest.mark.anyio
async def test_imgproxy_metadata_stripper_request_failed() -> None:
    filesystem = AsyncMock(Filesystem)

    class AIterator(AsyncIterator[Filesystem]):
        _round: int = 0

        def __aiter__(self) -> AsyncIterator[Filesystem]:
            return self

        async def __anext__(self) -> Filesystem:
            if self._round == 0:
                self._round += 1
                return filesystem

            raise StopAsyncIteration

    response = Mock(Response)
    response.status_code = 404

    http_client = AsyncMock(AsyncClient)
    http_client.get.return_value = response

    filesystem_factory = Mock(BaseFilesystemFactory)
    filesystem_factory.return_value = AIterator()

    strip_metadata = IMGProxyMetadataStripper(Mock(IMGProxyMetadataStripUrlGenerator), http_client, filesystem_factory)

    with pytest.raises(MetadataStripperException):
        await strip_metadata("path/to/image.jpg")

    filesystem.write.assert_not_called()


@pytest.mark.anyio
async def test_imgproxy_image_optimizer() -> None:
    expected_path = "path/to/image-optimized.webp"
    processor = AsyncMock(IMGProxyImageProcessor, return_value=(expected_path, "image/webp"))
    optimize = IMGProxyImageOptimizer(processor)
    path = "path/to/image.jpg"

    optimized_path, media_type = await optimize(path)

    assert optimized_path == expected_path
    assert media_type == "image/webp"
    # For some reason assert_awaited_once_with() does not work, so we go through the hassle below
    assert len(processor.mock_calls) == 1
    _, args, _ = processor.mock_calls[0]
    assert len(args) == 2
    assert args[0] == path
    assert args[1] == "optimized"


@pytest.mark.anyio
async def test_imgproxy_thumbnail_generator() -> None:
    expected_path = "path/to/image-thumbnail.webp"
    processor = AsyncMock(IMGProxyImageProcessor, return_value=(expected_path, "image/webp"))
    optimize = IMGProxyThumbnailGenerator(processor)
    path = "path/to/image.jpg"

    thumbnail_path, media_type = await optimize(path)

    assert thumbnail_path == expected_path
    assert media_type == "image/webp"
    # For some reason assert_awaited_once_with() does not work, so we go through the hassle below
    assert len(processor.mock_calls) == 1
    _, args, _ = processor.mock_calls[0]
    assert len(args) == 2
    assert args[0] == path
    assert args[1] == "thumbnail"


@pytest.mark.anyio
async def test_image_optimizer_task() -> None:
    attachment = Attachment(original_filename="image.jpg", original_media_type="image/png", melding=Mock(Melding))
    attachment.file_path = "/path/to/image.jpg"

    optimized_path = "/path/to/image-optimized.webp"
    optimizer = AsyncMock(BaseImageOptimizer, return_value=(optimized_path, "image/webp"))
    repository = Mock(AttachmentRepository)

    run = ImageOptimizerTask(optimizer, repository)

    await run(attachment)

    assert attachment.optimized_path == optimized_path
    repository.save.assert_awaited_once_with(attachment)


@pytest.mark.anyio
async def test_thumbnail_generator_task() -> None:
    attachment = Attachment(original_filename="image.jpg", original_media_type="image/png", melding=Mock(Melding))
    attachment.file_path = "path/to/image.jpg"

    thumbnail_path = "path/to/image-thumbnail.webp"
    thumbnail_generator = AsyncMock(BaseThumbnailGenerator, return_value=(thumbnail_path, "image/webp"))
    repository = Mock(AttachmentRepository)

    run = ThumbnailGeneratorTask(thumbnail_generator, repository)

    await run(attachment)

    assert attachment.thumbnail_path == thumbnail_path
    repository.save.assert_awaited_once_with(attachment)


@pytest.mark.anyio
async def test_ingestor() -> None:
    filesystem = Mock(Filesystem)
    task_manager = Mock(BackgroundTasks)
    optimizer_task = Mock(ImageOptimizerTask)
    thumbnail_task = Mock(ThumbnailGeneratorTask)
    metadata_stripper = AsyncMock(BaseMetadataStripper)
    attachment = Attachment(original_filename="image.jpg", original_media_type="image/png", melding=Mock(Melding))
    ingest = Ingestor(
        AsyncMock(BaseMalwareScanner),
        filesystem,
        task_manager,
        optimizer_task,
        thumbnail_task,
        metadata_stripper,
        "/tmp",
    )

    async def iterate() -> AsyncIterator[bytes]:
        for chunk in [b"Hello", b"World", b"!", b"!", b"!", b"!"]:
            yield chunk

    iterator = iterate()

    await ingest(attachment, iterator)

    filesystem.makedirs.assert_awaited_once()
    filesystem.write_iterator.assert_awaited_once_with(attachment.file_path, iterator)
    metadata_stripper.assert_awaited_once_with(attachment.file_path)
    task_manager.add_task.assert_any_call(optimizer_task, attachment=attachment)
    task_manager.add_task.assert_any_call(thumbnail_task, attachment=attachment)


@pytest.mark.anyio
async def test_ingestor_skips_background_tasks_for_non_image() -> None:
    filesystem = Mock(Filesystem)
    task_manager = Mock(BackgroundTasks)
    optimizer_task = Mock(ImageOptimizerTask)
    thumbnail_task = Mock(ThumbnailGeneratorTask)
    metadata_stripper = AsyncMock(BaseMetadataStripper)
    attachment = Attachment(
        original_filename="document.pdf", original_media_type="application/pdf", melding=Mock(Melding)
    )
    ingest = Ingestor(
        AsyncMock(BaseMalwareScanner),
        filesystem,
        task_manager,
        optimizer_task,
        thumbnail_task,
        metadata_stripper,
        "/tmp",
    )

    async def iterate() -> AsyncIterator[bytes]:
        for chunk in [b"Hello", b"World"]:
            yield chunk

    iterator = iterate()

    await ingest(attachment, iterator)

    filesystem.makedirs.assert_awaited_once()
    filesystem.write_iterator.assert_awaited_once_with(attachment.file_path, iterator)
    metadata_stripper.assert_not_awaited()
    task_manager.add_task.assert_not_called()


@pytest.mark.anyio
async def test_ingestor_deletes_image_when_stripping_metadata_fails() -> None:
    filesystem = AsyncMock(Filesystem)
    task_manager = Mock(BackgroundTasks)
    metadata_stripper = AsyncMock(BaseMetadataStripper, side_effect=MetadataStripperException)
    attachment = Attachment(original_filename="image.jpg", original_media_type="image/jpeg", melding=Mock(Melding))
    ingest = Ingestor(
        AsyncMock(BaseMalwareScanner),
        filesystem,
        task_manager,
        Mock(ImageOptimizerTask),
        Mock(ThumbnailGeneratorTask),
        metadata_stripper,
        "/tmp",
    )

    async def iterate() -> AsyncIterator[bytes]:
        yield b"Hello"

    with pytest.raises(MetadataStripperException):
        await ingest(attachment, iterate())

    filesystem.delete.assert_awaited_once_with(attachment.file_path)
    task_manager.add_task.assert_not_called()
