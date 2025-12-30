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
   1. TextAnswer: `{"text": "This is my answer" }`
   2. TimeAnswer: `{"time": "14:30" }`
   3. DateAnswer: `{"value": "day - 1", label: "Yesterday the 23rd of December", converted_date: "2025-12-23" }`
   4. ValueLabelAnswer: `[{"value": "option_1", "label": "Option 1" }, {"value": "option_3", "label": "Option 3" }]`
3. The backend derives the AnswerType based on the question component type (for new answers) or based on the stored answer data (for existing answers) and uses the correct model for validation and storage. This is done in a `Depends()` step, instead of through Pydantic before the request hits the path operation. We do this because we want the backend to find out what type should be given, before it starts to validate the incoming request body. 
   1. This only works if the component type which is being answered is mapped to an answer type. The only exception is the panel component type which doesn't hold a question. 
       - See: `FormIoComponentToAnswerTypeMap` in models.py



### Alternatives Considered
- Keeping a single Answer model with optional fields for each answer type. This would make the model harder to validate, as we would need to check which fields are filled based on the question component type. It would also make it harder to extend in the future if we want to add more answer types.
- Using a JSON field to store the answer data. This would make it harder to query and filter answers based on their content, as we would need to parse the JSON data each time.
- Create different models to store different answer types but only accept one attribute (e.g., "answer") in our endpoints. Basically skipping consequence 2. This would make it more complex to validate and parse the data, as we would need to check the type of the data and convert it accordingly.

### References
- Feature Conditionele vragen en vraagtypes: https://gemeente-amsterdam.atlassian.net/browse/SIG-6879
- Backend PR: https://github.com/Amsterdam/meldingen/pull/609
