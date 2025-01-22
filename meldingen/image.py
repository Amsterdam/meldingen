import base64
import hashlib
import hmac
from abc import ABCMeta, abstractmethod
from typing import AsyncIterator
from uuid import uuid4

from fastapi import BackgroundTasks
from httpx import AsyncClient
from meldingen_core.image import BaseImageOptimizer, BaseIngestor, BaseThumbnailGenerator
from meldingen_core.malware import BaseMalwareScanner
from plugfs.filesystem import Filesystem
from starlette.status import HTTP_200_OK

from meldingen.models import Attachment
from meldingen.repositories import AttachmentRepository


class ImageOptimizerException(Exception): ...


class IMGProxySignatureGenerator:
    _key: str
    _salt: str

    def __init__(self, key: str, salt: str):
        self._key = key
        self._salt = salt

    def __call__(self, url_path: str) -> str:
        """We are expecting `url_path` to be the part of the imgproxy url that would follow the signature.
        For example: /rs:fill:300:400:0/g:sm/aHR0cDovL2V4YW1w/bGUuY29tL2ltYWdl/cy9jdXJpb3NpdHku/anBn.png
        See also: https://docs.imgproxy.net/usage/signing_url"""
        digest = hmac.new(
            bytes.fromhex(self._key), msg=bytes.fromhex(self._salt) + url_path.encode(), digestmod=hashlib.sha256
        ).digest()

        return base64.urlsafe_b64encode(digest).decode().rstrip("=")


class BaseIMGProxyUrlGenerator(metaclass=ABCMeta):
    @abstractmethod
    def __call__(self, image_path: str) -> str: ...


class IMGProxyImageOptimizerUrlGenerator(BaseIMGProxyUrlGenerator):
    _generate_signature: IMGProxySignatureGenerator
    _imgproxy_base_url: str

    def __init__(self, signature_generator: IMGProxySignatureGenerator, imgproxy_base_url: str):
        self._generate_signature = signature_generator
        self._imgproxy_base_url = imgproxy_base_url

    def __call__(self, image_path: str) -> str:
        url_path = f"/f:webp/plain/{image_path}"
        signature = self._generate_signature(url_path)

        return f"{self._imgproxy_base_url}/{signature}{url_path}"


class IMGProxyThumbnailUrlGenerator(BaseIMGProxyUrlGenerator):
    _generate_signature: IMGProxySignatureGenerator
    _imgproxy_base_url: str
    _width: int
    _height: int

    def __init__(
        self, signature_generator: IMGProxySignatureGenerator, imgproxy_base_url: str, width: int, height: int
    ):
        self._generate_signature = signature_generator
        self._imgproxy_base_url = imgproxy_base_url
        self._width = width
        self._height = height

    def __call__(self, image_path: str) -> str:
        url_path = f"/rs:auto:{self._width}:{self._height}/f:webp/plain/{image_path}"
        signature = self._generate_signature(url_path)

        return f"{self._imgproxy_base_url}/{signature}{url_path}"


class IMGProxyImageProcessor:
    _generate_url: BaseIMGProxyUrlGenerator
    _http_client: AsyncClient
    _filesystem: Filesystem

    def __init__(self, url_generator: BaseIMGProxyUrlGenerator, http_client: AsyncClient, filesystem: Filesystem):
        self._generate_url = url_generator
        self._http_client = http_client
        self._filesystem = filesystem

    async def __call__(self, image_path: str, suffix: str) -> str:
        imgproxy_url = self._generate_url(image_path)

        file_path, _ = image_path.rsplit(".", 1)
        processed_path = f"{file_path}-{suffix}.webp"

        async with self._http_client.stream("GET", imgproxy_url) as response:
            if response.status_code != HTTP_200_OK:
                raise ImageOptimizerException()

            await self._filesystem.write_iterator(processed_path, response.aiter_bytes())

        return processed_path


class IMGProxyImageOptimizer(BaseImageOptimizer):
    _process: IMGProxyImageProcessor

    def __init__(self, img_proxy_processor: IMGProxyImageProcessor):
        self._process = img_proxy_processor

    async def __call__(self, image_path: str) -> str:
        return await self._process(image_path, "optimized")


class IMGProxyThumbnailGenerator(BaseThumbnailGenerator):
    _process: IMGProxyImageProcessor

    def __init__(self, img_proxy_processor: IMGProxyImageProcessor):
        self._process = img_proxy_processor

    async def __call__(self, image_path: str) -> str:
        return await self._process(image_path, "thumbnail")


class ImageOptimizerTask:
    _optimizer: BaseImageOptimizer
    _repository: AttachmentRepository

    def __init__(self, optimizer: BaseImageOptimizer, repository: AttachmentRepository):
        self._optimizer = optimizer
        self._repository = repository

    async def __call__(self, attachment: Attachment) -> None:
        attachment.optimized_path = await self._optimizer(attachment.file_path)

        await self._repository.save(attachment)


class ThumbnailGeneratorTask:
    _thumbnail_generator: BaseThumbnailGenerator
    _repository: AttachmentRepository

    def __init__(self, thumbnail_generator: BaseThumbnailGenerator, repository: AttachmentRepository):
        self._thumbnail_generator = thumbnail_generator
        self._repository = repository

    async def __call__(self, attachment: Attachment) -> None:
        attachment.thumbnail_path = await self._thumbnail_generator(attachment.file_path)

        await self._repository.save(attachment)


class Ingestor(BaseIngestor[Attachment]):
    _filesystem: Filesystem
    _background_task_manager: BackgroundTasks
    _image_optimizer_task: ImageOptimizerTask
    _thumbnail_generator_task: ThumbnailGeneratorTask
    _base_directory: str

    def __init__(
        self,
        scanner: BaseMalwareScanner,
        filesystem: Filesystem,
        background_task_manager: BackgroundTasks,
        image_optimizer_task: ImageOptimizerTask,
        thumbnail_generator_task: ThumbnailGeneratorTask,
        base_directory: str,
    ):
        super().__init__(scanner)

        self._filesystem = filesystem
        self._background_task_manager = background_task_manager
        self._image_optimizer_task = image_optimizer_task
        self._thumbnail_generator_task = thumbnail_generator_task
        self._base_directory = base_directory

    async def __call__(self, attachment: Attachment, data: AsyncIterator[bytes]) -> None:
        path = f"{self._base_directory}/{str(uuid4()).replace("-", "/")}/"
        attachment.file_path = path + attachment.original_filename

        await self._filesystem.makedirs(path)
        await self._filesystem.write_iterator(attachment.file_path, data)

        await self._scan_for_malware(attachment.file_path)

        self._background_task_manager.add_task(self._image_optimizer_task, attachment=attachment)
        self._background_task_manager.add_task(self._thumbnail_generator_task, attachment=attachment)
