from abc import ABCMeta

from meldingen_core.exceptions import NotFoundException
from meldingen_core.statemachine import BaseMeldingStateMachine, MeldingStates, get_all_backoffice_states
from mp_fsm.statemachine import BaseGuard, BaseStateMachine, BaseTransition

from meldingen.models import Melding
from meldingen.repositories import AnswerRepository, FormRepository


# guards
class HasLocation(BaseGuard[Melding]):
    async def __call__(self, obj: Melding) -> bool:
        return obj.geo_location is not None


class HasAnsweredRequiredQuestions(BaseGuard[Melding]):
    _answer_repository: AnswerRepository
    _form_repository: FormRepository

    def __init__(self, answer_repository: AnswerRepository, form_repository: FormRepository) -> None:
        self._answer_repository = answer_repository
        self._form_repository = form_repository

    async def __call__(self, obj: Melding) -> bool:
        assert obj.classification_id is not None

        try:
            form = await self._form_repository.find_by_classification_id(obj.classification_id)
        except NotFoundException:
            # No form means no required questions
            return True

        answers = await self._answer_repository.find_by_melding(obj.id)
        answered_question_ids = [answer.question_id for answer in answers]
        questions = await form.awaitable_attrs.questions

        for question in questions:
            component = await question.awaitable_attrs.component

            if component is not None and component.required is True and question.id not in answered_question_ids:
                return False

        return True


# transitions
class Classify(BaseTransition[Melding]):
    @property
    def from_states(self) -> list[str]:
        return [
            MeldingStates.NEW,
            MeldingStates.CLASSIFIED,
            MeldingStates.QUESTIONS_ANSWERED,
            MeldingStates.LOCATION_SUBMITTED,
            MeldingStates.ATTACHMENTS_ADDED,
            MeldingStates.CONTACT_INFO_ADDED,
        ]

    @property
    def to_state(self) -> str:
        return MeldingStates.CLASSIFIED


class AnswerQuestions(BaseTransition[Melding]):
    _guards: list[BaseGuard[Melding]]

    def __init__(self, guards: list[BaseGuard[Melding]]):
        self._guards = guards

    @property
    def from_states(self) -> list[str]:
        return [
            MeldingStates.CLASSIFIED,
            MeldingStates.QUESTIONS_ANSWERED,
            MeldingStates.LOCATION_SUBMITTED,
            MeldingStates.ATTACHMENTS_ADDED,
            MeldingStates.CONTACT_INFO_ADDED,
        ]

    @property
    def to_state(self) -> str:
        return MeldingStates.QUESTIONS_ANSWERED

    @property
    def guards(self) -> list[BaseGuard[Melding]]:
        return self._guards


class SubmitLocation(BaseTransition[Melding]):
    _guards: list[BaseGuard[Melding]]

    def __init__(self, guards: list[BaseGuard[Melding]]):
        self._guards = guards

    @property
    def from_states(self) -> list[str]:
        return [
            MeldingStates.QUESTIONS_ANSWERED,
            MeldingStates.LOCATION_SUBMITTED,
            MeldingStates.ATTACHMENTS_ADDED,
            MeldingStates.CONTACT_INFO_ADDED,
        ]

    @property
    def to_state(self) -> str:
        return MeldingStates.LOCATION_SUBMITTED

    @property
    def guards(self) -> list[BaseGuard[Melding]]:
        return self._guards


class AddAttachments(BaseTransition[Melding]):
    @property
    def from_states(self) -> list[str]:
        return [MeldingStates.LOCATION_SUBMITTED, MeldingStates.ATTACHMENTS_ADDED, MeldingStates.CONTACT_INFO_ADDED]

    @property
    def to_state(self) -> str:
        return MeldingStates.ATTACHMENTS_ADDED


class AddContactInfo(BaseTransition[Melding]):
    @property
    def from_states(self) -> list[str]:
        return [MeldingStates.ATTACHMENTS_ADDED, MeldingStates.CONTACT_INFO_ADDED]

    @property
    def to_state(self) -> str:
        return MeldingStates.CONTACT_INFO_ADDED


class Submit(BaseTransition[Melding]):
    @property
    def from_states(self) -> list[str]:
        return [
            MeldingStates.CONTACT_INFO_ADDED,
            MeldingStates.PLANNED,
            MeldingStates.AWAITING_PROCESSING,
            MeldingStates.PROCESSING,
            MeldingStates.REOPENED,
        ]

    @property
    def to_state(self) -> str:
        return MeldingStates.SUBMITTED


class RequestProcessing(BaseTransition[Melding]):
    @property
    def from_states(self) -> list[str]:
        return [MeldingStates.SUBMITTED]

    @property
    def to_state(self) -> str:
        return MeldingStates.AWAITING_PROCESSING


class Plan(BaseTransition[Melding]):
    @property
    def from_states(self) -> list[str]:
        return [MeldingStates.SUBMITTED, MeldingStates.AWAITING_PROCESSING]

    @property
    def to_state(self) -> str:
        return MeldingStates.PLANNED


class Process(BaseTransition[Melding]):
    @property
    def from_states(self) -> list[str]:
        return [
            MeldingStates.SUBMITTED,
            MeldingStates.AWAITING_PROCESSING,
            MeldingStates.PLANNED,
            MeldingStates.CANCELED,
            MeldingStates.REOPENED,
        ]

    @property
    def to_state(self) -> str:
        return MeldingStates.PROCESSING


class Complete(BaseTransition[Melding]):
    @property
    def from_states(self) -> list[str]:
        return [
            MeldingStates.SUBMITTED,
            MeldingStates.AWAITING_PROCESSING,
            MeldingStates.PROCESSING,
            MeldingStates.PLANNED,
            MeldingStates.REOPEN_REQUESTED,
            MeldingStates.REOPENED,
        ]

    @property
    def to_state(self) -> str:
        return MeldingStates.COMPLETED


class RequestReopen(BaseTransition[Melding]):
    @property
    def from_states(self) -> list[str]:
        return [MeldingStates.COMPLETED]

    @property
    def to_state(self) -> str:
        return MeldingStates.REOPEN_REQUESTED


class Reopen(BaseTransition[Melding]):
    @property
    def from_states(self) -> list[str]:
        return [MeldingStates.REOPEN_REQUESTED, MeldingStates.COMPLETED]

    @property
    def to_state(self) -> str:
        return MeldingStates.REOPENED


class Cancel(BaseTransition[Melding]):
    @property
    def from_states(self) -> list[str]:
        return [
            MeldingStates.SUBMITTED,
            MeldingStates.AWAITING_PROCESSING,
            MeldingStates.PROCESSING,
            MeldingStates.PLANNED,
            MeldingStates.REOPEN_REQUESTED,
            MeldingStates.REOPENED,
        ]

    @property
    def to_state(self) -> str:
        return MeldingStates.CANCELED


# state machine
class MpFsmMeldingStateMachine(BaseStateMachine[Melding]):
    __transitions: dict[str, BaseTransition[Melding]]

    def __init__(self, transitions: dict[str, BaseTransition[Melding]]):
        self.__transitions = transitions

    @property
    def _transitions(self) -> dict[str, BaseTransition[Melding]]:
        return self.__transitions


class MeldingStateMachine(BaseMeldingStateMachine[Melding]):
    _state_machine: MpFsmMeldingStateMachine

    def __init__(self, state_machine: MpFsmMeldingStateMachine):
        self._state_machine = state_machine

    async def transition(self, melding: Melding, transition_name: str) -> None:
        await self._state_machine.transition(melding, transition_name)
