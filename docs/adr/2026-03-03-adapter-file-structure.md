## Adapter file structure

### Status
Accepted

### Date accepted
2025-12-23

### Context
Different adapters should not be in the same file. They are different concerns and should be separated for better readability and maintainability.
Furthermore we hope this makes it easier to add new adapters in the future without having to modify an existing file. 
This will be especially helpful in case other implementations want to add adapters through forks. 

### Consequences
- This makes our adapter architecture more clear
- This makes it easier to add new adapters in the future without having to modify an existing file.

### Alternatives Considered
- Creating folders for services/domains and then adding the adapters there. That would create a more nested folder structure. Maybe needed later, but not now.
