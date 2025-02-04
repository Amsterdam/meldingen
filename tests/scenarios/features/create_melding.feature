Feature: Melding Form
    As a melder
    I want to be able to create a melding
    In order to have my issue resolved by the municipality

    Scenario: Create melding
        # Initial melding and classification
        Given there is a classification test
        When I create a melding with text "test"
        Then the melding should be classified as "test"
        And the state of the melding should be "classified"
        And the melding should contain a token
        # Additional questions
        Given there is a form for additional questions
        And the form contains a panel
        And the panel contains a text area component with the question "question"
        When I retrieve the additional questions through my classification
        And answer the additional questions with the text "text"
        And finish answering the additional questions by going to the next step
        Then the state of the melding should be "questions_answered"
        # Attachments
        Given I have a file "amsterdam-logo.jpg" that I want to attach to the melding
        And it is in my file system
        When I upload the file
        Then the upload response should include data about my file as attachment
        When I check the attachments of my melding
        Then there should be 1 attachments
        And the attachments should contain my file
        When I am finished with adding attachments
        Then the state of the melding should be "attachments_added"
        # Location
        Given I know the latitude 52.3680605 and longitude 4.897092 values of my melding
        When I add the location as geojson to my melding
        Then the location should be attached to the melding
        When I finalize submitting the location to my melding
        Then the state of the melding should be "location_submitted"
