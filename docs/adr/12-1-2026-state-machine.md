## Architecture of the state machine

### Status
Accepted

### Date accepted
2026-01-12

### Context
We require a robust system to manage the state of the meldingen. This ensures that meldingen are processed correctly and consistently throughout their lifecycle.

We should be able to define states and transitions between those states, along with guards that control when transitions can occur.

Lastly, we should differentiate between form states and backoffice states.


### Consequences

In meldingen-core, we define four lists in Enums:

- Form States
- Backoffice States
- All States
- Transitions

There, we also define what a state machine should be able to do (transition a state given a Melding and a transition name).

In meldingen, we implement the state machine logic. This includes defining the specific states, transitions, and guards for our meldingen. We use the base package `mp_fsm` as the base for out state machine.

The transitions take the form of:

```python
from meldingen_core.statemachine import MeldingStates
from mp_fsm.statemachine import BaseTransition

from meldingen.models import Melding


class AddContactInfo(BaseTransition[Melding]):
    @property
    def from_states(self) -> list[str]:
        return [MeldingStates.ATTACHMENTS_ADDED, MeldingStates.CONTACT_INFO_ADDED]

    @property
    def to_state(self) -> str:
        return MeldingStates.CONTACT_INFO_ADDED
```

A guard is a simple function that takes a Melding and returns a boolean:

```python
from mp_fsm.statemachine import BaseGuard

from meldingen.models import Melding

class HasLocation(BaseGuard[Melding]):
    async def __call__(self, obj: Melding) -> bool:
        return obj.geo_location is not None
```

The state machine is then created as follows:

```python
def melding_state_machine(
    has_answered_required_questions: Annotated[HasAnsweredRequiredQuestions, Depends(has_answered_required_questions)],
) -> MeldingStateMachine:
    return MeldingStateMachine(
        MpFsmMeldingStateMachine(
            {
                MeldingTransitions.CLASSIFY: Classify(),
                MeldingTransitions.ANSWER_QUESTIONS: AnswerQuestions([has_answered_required_questions]),
                MeldingTransitions.SUBMIT_LOCATION: SubmitLocation([HasLocation()]),
                MeldingTransitions.ADD_ATTACHMENTS: AddAttachments(),
                MeldingTransitions.ADD_CONTACT_INFO: AddContactInfo(),
                MeldingTransitions.SUBMIT: Submit(),
                MeldingTransitions.REQUEST_PROCESSING: RequestProcessing(),
                MeldingTransitions.PROCESS: Process(),
                MeldingTransitions.PLAN: Plan(),
                MeldingTransitions.CANCEL: Cancel(),
                MeldingTransitions.REQUEST_REOPEN: RequestReopen(),
                MeldingTransitions.REOPEN: Reopen(),
                MeldingTransitions.COMPLETE: Complete(),
            }
        )
    )

```

Finally, we use the BaseStateTransitionAction from meldingen-core to perform the state change:

```python
class MeldingRequestReopenAction(BaseStateTransitionAction[T]):
    @property
    def transition_name(self) -> str:
        return MeldingTransitions.REQUEST_REOPEN
```

and use this action in our endpoint:

```python
@router.put(
    "/{melding_id}/request_reopen",
    name="melding:request-reopen",
    responses={
        **transition_not_allowed,
        **unauthorized_response,
        **not_found_response,
        **default_response,
    },
    dependencies=[Depends(authenticate_user)],
)
async def request_reopen_melding(
    melding_id: Annotated[int, Path(description="The id of the melding.", ge=1)],
    action: Annotated[MeldingRequestReopenAction[Melding], Depends(melding_request_reopen_action)],
    produce_output: Annotated[MeldingOutputFactory, Depends(melding_output_factory)],
) -> MeldingOutput:
    try:
        melding = await action(melding_id)
    except NotFoundException:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND)
    except WrongStateException:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Transition not allowed from current state")

    return await produce_output(melding)
```

### Alternatives Considered

mp-fsm was created by the Gemeente Amsterdam to comply with our demands of a fully-typed finite state machine, built with Meldingen in mind.

### References

- See `docs/statemachines` for the state machine definitions.
- https://github.com/Amsterdam/mp-fsm