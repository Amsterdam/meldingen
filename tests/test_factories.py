from meldingen.factories import AttachmentFactory
from meldingen.models import Melding, Attachment


def test_attachment_factory() -> None:
    factory = AttachmentFactory()
    attachment = factory("original_filename.txt", Melding("melding text"))

    assert isinstance(attachment, Attachment)
