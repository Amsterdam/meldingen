from meldingen_core.actions.attachment import DeleteAttachmentAction as BaseDeleteAttachmentAction
from meldingen_core.actions.attachment import DownloadAttachmentAction as BaseDownloadAttachmentAction
from meldingen_core.actions.attachment import ListAttachmentsAction as BaseListAttachmentsAction
from meldingen_core.actions.attachment import MelderDeleteAttachmentAction as BaseMelderDeleteAttachmentAction
from meldingen_core.actions.attachment import MelderDownloadAttachmentAction as BaseMelderDownloadAttachmentAction
from meldingen_core.actions.attachment import UploadAttachmentAction as BaseUploadAttachmentAction

from meldingen.models import Attachment, Melding, User


class UploadAttachmentAction(BaseUploadAttachmentAction[Attachment, Melding, User]): ...


class MelderUploadAttachmentAction(BaseUploadAttachmentAction[Attachment, Melding, None]): ...


class DownloadAttachmentAction(BaseDownloadAttachmentAction[Attachment]): ...


class ListAttachmentsAction(BaseListAttachmentsAction[Attachment]): ...


class DeleteAttachmentAction(BaseDeleteAttachmentAction[Attachment]): ...


class MelderDeleteAttachmentAction(BaseMelderDeleteAttachmentAction[Attachment, Melding]): ...


class MelderDownloadAttachmentAction(BaseMelderDownloadAttachmentAction[Attachment, Melding]): ...
