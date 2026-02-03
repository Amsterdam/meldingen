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
        # Location
        Given I know the latitude 52.3680605 and longitude 4.897092 values of my melding
        When I add the location as geojson to my melding
        Then the location should be attached to the melding
        When I finish my current step by completing "SUBMIT_LOCATION"
        Then I should receive a response with the current content of my melding
        And the state of the melding should be "location_submitted"
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
        And a confirmation email should be sent to "test@example.com"

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
        # Location
        When I finish my current step by completing "SUBMIT_LOCATION"
        Then I should be told to submit my location first

  Scenario Outline: A melding in the state classified can't skip any steps
        # Initial melding and classification
        When I create a melding with text "test"
        Then the melding should be classified as "test"
        And the state of the melding should be "classified"
        And the melding should contain a token

        When I finish my current step by completing "<transition>"
        Then I should be told that this transition is not allowed from the current state

        Examples:
        | transition |
        | ADD_ATTACHMENTS |
        | SUBMIT_LOCATION |
        | ADD_CONTACT_INFO |
        | SUBMIT           |

    Scenario Outline: A melding in the state questions_answered can't skip any steps
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

        When I finish my current step by completing "<transition>"
        Then I should be told that this transition is not allowed from the current state

        Examples:
        | transition |
        | ADD_ATTACHMENTS |
        | ADD_CONTACT_INFO |
        | SUBMIT           |

    Scenario Outline: A melding in the state location_submitted can't skip any steps
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
        # Location
        Given I know the latitude 52.3680605 and longitude 4.897092 values of my melding
        When I add the location as geojson to my melding
        Then the location should be attached to the melding
        When I finish my current step by completing "SUBMIT_LOCATION"
        Then I should receive a response with the current content of my melding
        And the state of the melding should be "location_submitted"

        When I finish my current step by completing "<transition>"
        Then I should be told that this transition is not allowed from the current state

        Examples:
        | transition |
        | ADD_CONTACT_INFO |
        | SUBMIT           |

    Scenario Outline: A melding in the state attachments_added can't skip any steps
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
        # Location
        Given I know the latitude 52.3680605 and longitude 4.897092 values of my melding
        When I add the location as geojson to my melding
        Then the location should be attached to the melding
        When I finish my current step by completing "SUBMIT_LOCATION"
        Then I should receive a response with the current content of my melding
        And the state of the melding should be "location_submitted"
        # Attachments
        When I finish my current step by completing "ADD_ATTACHMENTS"
        Then I should receive a response with the current content of my melding
        And the state of the melding should be "attachments_added"

        When I finish my current step by completing "<transition>"
        Then I should be told that this transition is not allowed from the current state

        Examples:
        | transition |
        | SUBMIT           |

    Scenario Outline: A melding in the state contact_info_added can go back to all previous states
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
        # Location
        Given I know the latitude 52.3680605 and longitude 4.897092 values of my melding
        When I add the location as geojson to my melding
        Then the location should be attached to the melding
        When I finish my current step by completing "SUBMIT_LOCATION"
        Then I should receive a response with the current content of my melding
        And the state of the melding should be "location_submitted"
        # Attachments
        When I finish my current step by completing "ADD_ATTACHMENTS"
        Then I should receive a response with the current content of my melding
        And the state of the melding should be "attachments_added"

        When I finish my current step by completing "<transition>"
        Then I should receive a response with the current content of my melding

        Examples:
        | transition |
        | ANSWER_QUESTIONS |
        | ADD_ATTACHMENTS |
        | SUBMIT_LOCATION |
        | ADD_CONTACT_INFO |

    Scenario: A melding that has been submitted can not go back to a previous state
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
        # Location
        Given I know the latitude 52.3680605 and longitude 4.897092 values of my melding
        When I add the location as geojson to my melding
        Then the location should be attached to the melding
        When I finish my current step by completing "SUBMIT_LOCATION"
        Then I should receive a response with the current content of my melding
        And the state of the melding should be "location_submitted"
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
        # Go back
        When I finish my current step by completing "<transition>"
        Then I should be told that I am not allowed to change the state because the token has been invalidated

        Examples:
        | transition |
        | ANSWER_QUESTIONS |
        | ADD_ATTACHMENTS |
        | SUBMIT_LOCATION |
        | ADD_CONTACT_INFO |

    Scenario: A melder can add an asset to a melding
        # Initial melding and classification with asset type
        Given there is an asset type containers with max_assets 3
        And the classification test has asset type containers
        When I create a melding with text "test"
        Then the melding should be classified as "test"
        And the state of the melding should be "classified"
        And the melding should contain a token
        # Add asset
        When I add an asset with external_id "container-123" to my melding
        Then the asset should be added successfully
        And the melding should have 1 asset(s)

    Scenario: A melder cannot exceed max_assets limit
        # Initial melding and classification with asset type
        Given there is an asset type containers with max_assets 2
        And the classification test has asset type containers
        When I create a melding with text "test"
        Then the melding should be classified as "test"
        And the state of the melding should be "classified"
        And the melding should contain a token
        # Add first asset
        When I add an asset with external_id "container-1" to my melding
        Then the asset should be added successfully
        And the melding should have 1 asset(s)
        # Add second asset
        When I add an asset with external_id "container-2" to my melding
        Then the asset should be added successfully
        And the melding should have 2 asset(s)
        # Try to add third asset (should fail)
        When I add an asset with external_id "container-3" to my melding
        Then I should be told that the maximum number of assets has been reached
        And the melding should have 2 asset(s)

    Scenario: A melder can add an asset after removing one when at max_assets
        # Initial melding and classification with asset type
        Given there is an asset type containers with max_assets 2
        And the classification test has asset type containers
        When I create a melding with text "test"
        Then the melding should be classified as "test"
        And the state of the melding should be "classified"
        And the melding should contain a token
        # Add first asset
        When I add an asset with external_id "container-1" to my melding
        Then the asset should be added successfully
        And the melding should have 1 asset(s)
        # Add second asset
        When I add an asset with external_id "container-2" to my melding
        Then the asset should be added successfully
        And the melding should have 2 asset(s)
        # Try to add third asset (should fail)
        When I add an asset with external_id "container-3" to my melding
        Then I should be told that the maximum number of assets has been reached
        And the melding should have 2 asset(s)
        # Remove first asset
        When I remove the asset with external_id "container-1" from my melding
        Then the asset should be removed successfully
        And the melding should have 1 asset(s)
        # Add third asset (should now succeed)
        When I add an asset with external_id "container-3" to my melding
        Then the asset addition should succeed
        And the melding should have 2 asset(s)