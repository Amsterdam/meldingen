from meldingen_core.actions.attachment import DeleteAttachmentAction as BaseDeleteAttachmentAction
from meldingen_core.actions.attachment import DownloadAttachmentAction as BaseDownloadAttachmentAction
from meldingen_core.actions.attachment import ListAttachmentsAction as BaseListAttachmentsAction
from meldingen_core.actions.attachment import MelderDeleteAttachmentAction as BaseMelderDeleteAttachmentAction
from meldingen_core.actions.attachment import UploadAttachmentAction as BaseUploadAttachmentAction

from meldingen.models import Attachment, Melding, User


class UploadAttachmentAction(BaseUploadAttachmentAction[Attachment, Melding, User]): ...


class DownloadAttachmentAction(BaseDownloadAttachmentAction[Attachment, Melding]): ...


class ListAttachmentsAction(BaseListAttachmentsAction[Attachment]): ...


class DeleteAttachmentAction(BaseDeleteAttachmentAction[Attachment]): ...


class MelderDeleteAttachmentAction(BaseMelderDeleteAttachmentAction[Attachment, Melding]): ...
