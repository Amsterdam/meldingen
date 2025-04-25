# State Machine
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
