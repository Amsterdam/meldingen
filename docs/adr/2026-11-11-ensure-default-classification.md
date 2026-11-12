## Title
Ensure every melding has a classification

### Status
Accepted

### Date accepted
October 15, 2026 at 3:17 PM

### Context
The data model allows a melding to have no classification. This makes it harder to determine how such a melding should be handled based on its classification.

#### Application model
The classifier interface allows no classification (`None`) as a result, and the data model allows a melding to have no classification. The classification adapter validates generated names against classifications available in the database, so an arbitrary or non-existent name is not an expected result.

If every melding is assigned a classification, application code does not need to handle a missing classification as a separate case.

#### User experience
Behandelaren use the `Overig` classification for meldingen that need specific routing. Treating meldingen without a classification as a separate `None` category would require behandelaren to check both categories for this work and would add another state for the interface to display, filter, and order.

The confirmation-email task reads the service-level objective from the melding's classification. Without a classification, it cannot obtain a classification-specific objective. Assigning a fallback classification provides one whose objective can be configured.

### Consequences
- The default classification must exist and must not be deleted or renamed.
- Data migrations must ensure the default classification has a configured service-level objective.
- The default classification must be loaded from the database.

### Alternatives Considered
Set the database default for a melding's classification to the configured default classification.

### References
See also: SIG-7790