## Different Answer Models

### Status
Accepted

### Date accepted
2025-12-23

### Context
With the introduction of new FormIOComponents to answer questions about dates and times, the simple Answer model that could only save a string as an answer was no longer sufficient.
To accommodate different types of answers (e.g., text, date, time and values and labels), we have decided to create separate models for each answer type. This allows us to validate each answer coming in and store them in a more structured way.
It also allows the backend to save more metadata, such as the converted date for date answers, which can be useful for reporting and filtering.

### Consequences 
This required the following changes: 
1. Creation of new Answer model subclasses (e.g., TextAnswer, DateAnswer, TimeAnswer, ValueLabelAnswer). Each model requires different fields to store the answer, but they are stored in the same database table. Through polymorphic identities on the type column, the backend determines which subclass to create. 
2. The frontend has to determine what shape the answer has based on the FormIOQuestionComponent and send the correct data structure to the backend. For example:  
   1. TextAnswer: `{"text": "This is my answer", "type: "text" }`
   2. TimeAnswer: `{"time": "14:30" , "type": "time" }`
   3. DateAnswer: `{"date": {"value": "day - 1", label: "Yesterday the 23rd of December", converted_date: "2025-12-23"}, "type": "date" }`
   4. ValueLabelAnswer: `{"values_and_labels": [{"value": "option_1", "label": "Option 1" }, {"value": "option_3", "label": "Option 3" }, ], "type": "value_label"}`
3. The backend derives the AnswerType based on the question component type (for new answers) or based on the stored answer data (for existing answers) and uses the correct model for validation and storage.
   1. This only works if the question component type which is being answered is mapped to an answer type. The only exception is the panel component type which doesn't hold a question. 
       - See: `FormIoComponentToAnswerTypeMap` in models.py



### Alternatives Considered
- Keeping a single Answer model with optional fields for each answer type. This would make the model harder to validate, as we would need to check which fields are filled based on the question component type. It would also make it harder to extend in the future if we want to add more answer types.
- Using a JSON field to store the answer data. This would make it harder to query and filter answers based on their content, as we would need to parse the JSON data each time.
- Create different models to store different answer types but only accept one attribute (e.g., "answer") in our endpoints. Basically skipping consequence 2. Besides the extra conversion step, this would make it more vague on what the jsonlogic conditions should look like when created in a FormIO Question Component. This is because the jsonlogic will be evaluted on the "text" attribute whereas the POST body would contain an "answer" attribute. 

### References
- Feature Conditionele vragen en vraagtypes: https://gemeente-amsterdam.atlassian.net/browse/SIG-6879
- Backend PR: https://github.com/Amsterdam/meldingen/pull/609

