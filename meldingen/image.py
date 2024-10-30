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
