import secrets
import string


class PublicIdGenerator:
    _alphabet: str

    def __init__(self, alphabet: str | None = None):
        if alphabet is None:
            self._alphabet = string.ascii_uppercase + string.digits
        else:
            self._alphabet = alphabet

    def __call__(self, length: int = 6) -> str:
        return "".join(secrets.choice(self._alphabet) for _ in range(length))
