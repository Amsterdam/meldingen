import base64
import hashlib
import hmac

from httpx import AsyncClient
from meldingen_core.image import BaseImageOptimizer
from plugfs.filesystem import Filesystem
from starlette.status import HTTP_200_OK


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


class IMGProxyImageOptimizerUrlGenerator:
    _generate_signature: IMGProxySignatureGenerator
    _imgproxy_base_url: str

    def __init__(self, signature_generator: IMGProxySignatureGenerator, imgproxy_base_url: str):
        self._generate_signature = signature_generator
        self._imgproxy_base_url = imgproxy_base_url

    def __call__(self, image_url: str) -> str:
        url_path = f"/f:webp/plain/{image_url}"
        signature = self._generate_signature(url_path)

        return f"{self._imgproxy_base_url}/{signature}{url_path}"


class IMGProxyImageOptimizer(BaseImageOptimizer):
    _generate_url: IMGProxyImageOptimizerUrlGenerator
    _filesystem: Filesystem
    _http_client: AsyncClient

    def __init__(
        self, url_generator: IMGProxyImageOptimizerUrlGenerator, filesystem: Filesystem, http_client: AsyncClient
    ):
        self._generate_url = url_generator
        self._filesystem = filesystem
        self._http_client = http_client

    async def __call__(self, image_path: str) -> str:
        imgproxy_url = self._generate_url(image_path)

        file_path, _ = image_path.rsplit(".", 1)
        optimized_path = f"{file_path}-optimized.webp"

        async with self._http_client.stream("GET", imgproxy_url) as response:
            await self._filesystem.write_iterator(optimized_path, response.aiter_bytes())

        if response.status_code != HTTP_200_OK:
            raise ImageOptimizerException()

        return optimized_path
