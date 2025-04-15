from meldingen.factories import AttachmentFactory
from meldingen.models import Attachment, Melding


def test_attachment_factory() -> None:
    factory = AttachmentFactory()
    attachment = factory("original_filename.txt", Melding("melding text"), "image/png")

    assert isinstance(attachment, Attachment)
