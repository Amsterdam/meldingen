# Melding Process State Machine
This flow chart represents the state machine for the processing of a "melding" in the backoffice. It outlines the various states a melding goes through from submission until completion or cancellation.
The diagram only contains the states and transitions that are defined for Release 1 of the backoffice system.
## Diagram
```mermaid

stateDiagram-v2
    direction LR

    [*] --> SUBMITTED 

    SUBMITTED  --> AWAITING_PROCESSING 
    SUBMITTED  --> PROCESSING 
    SUBMITTED  --> COMPLETED 
    SUBMITTED  --> CANCELED 
    SUBMITTED  --> PLANNED 

    AWAITING_PROCESSING  --> SUBMITTED 
    AWAITING_PROCESSING  --> PLANNED 
    AWAITING_PROCESSING  --> COMPLETED 
    AWAITING_PROCESSING  --> PROCESSING 
    AWAITING_PROCESSING  --> CANCELED 

    PROCESSING  --> SUBMITTED 
    PROCESSING  --> PLANNED 
    PROCESSING  --> COMPLETED 
    PROCESSING  --> CANCELED 

    PLANNED  --> SUBMITTED 
    PLANNED  --> PROCESSING 
    PLANNED  --> COMPLETED 
    PLANNED  --> CANCELED 
    
    CANCELED  --> REOPENED 
    CANCELED  --> PROCESSING
    
    COMPLETED  --> REOPENED 
    COMPLETED  --> REOPEN_REQUESTED
    
    REOPEN_REQUESTED --> COMPLETED
    REOPEN_REQUESTED --> REOPENED
    REOPEN_REQUESTED --> CANCELED
    
    REOPENED  --> PROCESSING 
    REOPENED  --> COMPLETED 
    REOPENED  --> CANCELED 
    REOPENED  --> SUBMITTED 
    
    COMPLETED  --> [*]
    CANCELED  --> [*]
    
    state COMPLETED <<end>>
    state CANCELED <<end>>
```
