from meldingen_core.labels import BaseLabelReplacer, InvalidLabelException

from meldingen.models import Label, Melding


class LabelReplacer(BaseLabelReplacer[Melding, Label]):

    async def __call__(self, melding: Melding, label_ids: list[int]) -> Melding:
        labels = await self._label_repository.list_by_ids(label_ids)

        if len(labels) != len(label_ids):
            retrieved_label_ids = [label.id for label in labels]
            unknown_label_ids = list(set(label_ids) - set(retrieved_label_ids))

            raise InvalidLabelException(f"Can't find labels with id's: {unknown_label_ids}")

        melding_labels = await melding.awaitable_attrs.labels
        melding_labels.clear()
        melding_labels.extend(labels)

        return melding
