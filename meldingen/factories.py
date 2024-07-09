from meldingen_core.factories import BaseAttachmentFactory

from meldingen.models import Attachment, Melding


class AttachmentFactory(BaseAttachmentFactory[Attachment, Melding]):
    def __call__(self, original_filename: str, melding: Melding) -> Attachment:
        return Attachment(original_filename, melding)
