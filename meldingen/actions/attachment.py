from meldingen_core.actions.attachment import DeleteAttachmentAction as BaseDeleteAttachmentAction
from meldingen_core.actions.attachment import DownloadAttachmentAction as BaseDownloadAttachmentAction
from meldingen_core.actions.attachment import ListAttachmentsAction as BaseListAttachmentsAction
from meldingen_core.actions.attachment import MelderDownloadAttachmentAction as BaseMelderDownloadAttachmentAction
from meldingen_core.actions.attachment import MelderListAttachmentsAction as BaseMelderListAttachmentsAction
from meldingen_core.actions.attachment import UploadAttachmentAction as BaseUploadAttachmentAction

from meldingen.models import Attachment, Melding


class UploadAttachmentAction(BaseUploadAttachmentAction[Attachment, Melding]): ...


class DownloadAttachmentAction(BaseDownloadAttachmentAction[Attachment]): ...


class MelderDownloadAttachmentAction(BaseMelderDownloadAttachmentAction[Attachment, Melding]): ...


class ListAttachmentsAction(BaseListAttachmentsAction[Attachment]): ...


class MelderListAttachmentsAction(BaseMelderListAttachmentsAction[Attachment, Melding]): ...


class DeleteAttachmentAction(BaseDeleteAttachmentAction[Attachment, Melding]): ...
