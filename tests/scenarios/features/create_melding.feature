Feature: Melding Form
    As a melder
    I want to be able to create a melding
    In order to have my issue resolved by the municipality

    Scenario: Create melding
        Given there is a classification test
        When I create a melding with text "test"
        Then the melding should be classified as "test"
        And the melding should have an id
        And the state of the melding should be "classified"
        And the melding should contain a token
        Given there is a form for additional questions
        And the form contains a panel
        And the panel contains a text area component with the question "question"
        When I retrieve the additional questions through my classification
        And I answer the additional questions with the text "text"
