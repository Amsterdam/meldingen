Feature: Melding Form
    As a user
    I want to be able to create a melding
    So that I can report a problem
    By going through all the steps in the melding form

    Scenario: Create a melding
        Given I have a problem that I want to report
          When I submit my problem to the primary form
#          And I continue to the classification step
#          And answer the additional questions returned by the classification
#          And submit these answers by going to the attachment step
#          And add an attachment to the melding
#          And submit the attachments by going to the location step
          And I fill in the location of the problem
#          And submit the location by going to the contact info step
#          And fill in my contact info
#          And submit the contact info
#          And continue to the summary step
#          And submit the melding
#            Then I should see "Melding created"
