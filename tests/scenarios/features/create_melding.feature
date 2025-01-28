Feature: Melding Form
    As a melder
    I want to be able to create a melding
    In order to have my issue resolved by the municipality

    Scenario: Create melding
        Given there is a classification test
        When I create a melding with text "test"
        Then the melding should be classified as "test"
