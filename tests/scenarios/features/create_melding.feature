Feature: Melding Form
    As a melder
    I want to be able to create a melding
    In order to have my issue resolved by the municipality

    Background:
        Given there is a classification test
        And there is a form for additional questions
        And the form contains a panel
        And the panel contains a text area component with the question "question"

    Scenario: A melder successfully submits a melding
        # Initial melding and classification
        When I create a melding with text "test"
        Then the melding should be classified as "test"
        And the state of the melding should be "classified"
        And the melding should contain a token
        # Additional questions
        When I retrieve the additional questions through my classification
        And I answer the additional questions with the text "text"
        And I finish my current step by completing "ANSWER_QUESTIONS"
        Then I should receive a response with the current content of my melding
        And the state of the melding should be "questions_answered"
        # Attachments
        Given I have a file "amsterdam-logo.jpg" that I want to attach to the melding
        And it is in my file system
        When I upload the file
        Then the upload response should include data about my file as attachment
        When I check the attachments of my melding
        Then there should be 1 attachments
        And the attachments should contain my file
        When I finish my current step by completing "ADD_ATTACHMENTS"
        Then I should receive a response with the current content of my melding
        And the state of the melding should be "attachments_added"
        # Location
        Given I know the latitude 52.3680605 and longitude 4.897092 values of my melding
        When I add the location as geojson to my melding
        Then the location should be attached to the melding
        When I finish my current step by completing "SUBMIT_LOCATION"
        Then I should receive a response with the current content of my melding
        And the state of the melding should be "location_submitted"
        # Contact information
        Given I have a phone number "+31612345678" and an email address "test@example.com"
        When I add the contact information to my melding
        Then the melding contains my contact information
        When I finish my current step by completing "ADD_CONTACT_INFO"
        Then I should receive a response with the current content of my melding
        And the state of the melding should be "contact_info_added"
        # Submit
        When I finish my current step by completing "SUBMIT"
        Then I should receive a response with the current content of my melding
        And the state of the melding should be "submitted"

    Scenario: A melding can't be submitted if not all required additional questions are answered
        # Initial melding and classification
        When I create a melding with text "test"
        Then the melding should be classified as "test"
        And the state of the melding should be "classified"
        And the melding should contain a token
        # Additional questions
        When I finish my current step by completing "ANSWER_QUESTIONS"
        Then I should be told to answer the additional questions first

    Scenario: A melding can't be submitted without a valid location
        # Initial melding and classification
        When I create a melding with text "test"
        Then the melding should be classified as "test"
        And the state of the melding should be "classified"
        And the melding should contain a token
        # Additional questions
        When I retrieve the additional questions through my classification
        And I answer the additional questions with the text "text"
        When I finish my current step by completing "ANSWER_QUESTIONS"
        Then I should receive a response with the current content of my melding
        And the state of the melding should be "questions_answered"
        # Attachments
        When I finish my current step by completing "ADD_ATTACHMENTS"
        Then I should receive a response with the current content of my melding
        And the state of the melding should be "attachments_added"
        # Location
        When I finish my current step by completing "SUBMIT_LOCATION"
        Then I should be told to submit my location first
