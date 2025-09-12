from abc import ABCMeta, abstractmethod
from collections.abc import AsyncIterator

from meldingen_core.factories import BaseAssetFactory, BaseAttachmentFactory
from plugfs.filesystem import Filesystem

from meldingen.models import Asset, AssetType, Attachment, Melding


class AttachmentFactory(BaseAttachmentFactory[Attachment, Melding]):
    def __call__(self, original_filename: str, melding: Melding, media_type: str) -> Attachment:
        return Attachment(original_filename=original_filename, original_media_type=media_type, melding=melding)


class BaseFilesystemFactory(metaclass=ABCMeta):
    @abstractmethod
    def __call__(self) -> AsyncIterator[Filesystem]: ...


class AzureFilesystemFactory(BaseFilesystemFactory):
    async def __call__(self) -> AsyncIterator[Filesystem]:
        from meldingen.dependencies import azure_container_client, filesystem, filesystem_adapter

        async for client in azure_container_client():
            _filesystem = filesystem(filesystem_adapter(client))
            yield _filesystem


class AssetFactory(BaseAssetFactory[Asset, AssetType, Melding]):
    def __call__(self, external_id: str, asset_type: AssetType, melding: Melding) -> Asset:
        return Asset(external_id, asset_type, melding)
