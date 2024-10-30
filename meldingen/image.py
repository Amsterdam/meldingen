import base64
import hashlib
import hmac


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

    def __init__(self, generate_signature: IMGProxySignatureGenerator, imgproxy_base_url: str):
        self._generate_signature = generate_signature
        self._imgproxy_base_url = imgproxy_base_url

    def __call__(self, image_url: str) -> str:
        url_path = f"/f:webp/{image_url}"
        signature = self._generate_signature(url_path)

        return f"{self._imgproxy_base_url}/{signature}{url_path}"
