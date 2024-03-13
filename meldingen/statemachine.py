from meldingen_core.statemachine import BaseMeldingStateMachine, MeldingStates
from mp_fsm.statemachine import BaseStateMachine, BaseTransition

from meldingen.models import Melding


class Process(BaseTransition[Melding]):
    @property
    def from_states(self) -> list[str]:
        return [MeldingStates.NEW]

    @property
    def to_state(self) -> str:
        return MeldingStates.PROCESSING


class Complete(BaseTransition[Melding]):
    @property
    def from_states(self) -> list[str]:
        return [MeldingStates.NEW, MeldingStates.PROCESSING]

    @property
    def to_state(self) -> str:
        return MeldingStates.COMPLETED


class MeldingStateMachine(BaseStateMachine[Melding], BaseMeldingStateMachine):
    __transitions: dict[str, BaseTransition[Melding]]

    def __init__(self, transitions: dict[str, BaseTransition[Melding]]):
        self.__transitions = transitions

    @property
    def _transitions(self) -> dict[str, BaseTransition[Melding]]:
        return self.__transitions
