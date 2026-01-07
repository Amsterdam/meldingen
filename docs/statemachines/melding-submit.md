# Melding Submission State Machine
This flow chart represents the state machine for the submission of a "melding" by a melder / reporter through our Melding Form. It outlines the various states a melding goes through from creation until completion when it can be processed by the backoffice. During processing the melding enters a new state and will follow another state machine, see: [melding-process.md](./melding-process.md). 
## Diagram
```mermaid
stateDiagram-v2
    [*] --> New
    state HasClassification <<choice>>
    New --> HasClassification
    HasClassification --> Classified: HasClassification
    Classified --> HasClassification
    HasClassification --> Classified: HasClassification
    state HasAnsweredRequiredQuestions <<choice>>
    Classified --> HasAnsweredRequiredQuestions
    HasAnsweredRequiredQuestions --> Questions_Answered: HasAnsweredRequiredQuestions
    state HasLocation <<choice>>
    Questions_Answered --> HasLocation
    HasLocation --> Location_Submitted: HasLocation
    Location_Submitted --> Attachments_Added
    Attachments_Added --> Contact_Info_Added
    Contact_Info_Added --> Submitted
    Submitted --> Processing
    Processing --> Completed
    Completed --> [*]
```
