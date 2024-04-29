from meldingen_core.statemachine import BaseMeldingStateMachine, MeldingStates
from mp_fsm.statemachine import BaseGuard, BaseStateMachine, BaseTransition

from meldingen.models import Melding


# guards
class HasClassification(BaseGuard[Melding]):
    async def __call__(self, obj: Melding) -> bool:
        return obj.classification is not None


# transitions
class Process(BaseTransition[Melding]):
    @property
    def from_states(self) -> list[str]:
        return [MeldingStates.NEW]

    @property
    def to_state(self) -> str:
        return MeldingStates.PROCESSING


class Classify(BaseTransition[Melding]):
    _guards: list[BaseGuard[Melding]]

    def __init__(self, guards: list[BaseGuard[Melding]]):
        self._guards = guards

    @property
    def from_states(self) -> list[str]:
        return [MeldingStates.NEW, MeldingStates.CLASSIFIED]

    @property
    def to_state(self) -> str:
        return MeldingStates.CLASSIFIED

    @property
    def guards(self) -> list[BaseGuard[Melding]]:
        return self._guards


class Complete(BaseTransition[Melding]):
    @property
    def from_states(self) -> list[str]:
        return [MeldingStates.NEW, MeldingStates.PROCESSING]

    @property
    def to_state(self) -> str:
        return MeldingStates.COMPLETED


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
