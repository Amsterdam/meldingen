import secrets
import string


class PublicIdGenerator:
    _alphabet: str

    def __init__(self, alphabet: str | None = None):
        self._alphabet = alphabet
        if alphabet is None:
            self._alphabet = string.ascii_uppercase + string.digits

    def __call__(self, length: int = 6) -> str:
        return "".join(secrets.choice(self._alphabet) for _ in range(length))
