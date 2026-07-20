## Seed files

This folder stores the seed files used to initialize the database with default or sample data. 
Seed files are stored as JSON and are imported in the `meldingen-entrypoint.sh` script through the Typer Command `python main.py seed` 

Examples of the structure of the seed files can be found in the `examples` folder. 

### Currently supported seed files

| Model          | Seed File Name     |  
|----------------|--------------------| 
| Classification | classifications.json  |  

### Behaviour

Seeding is **idempotent**. Classifications are upserted by their unique `name`:
new entries are inserted and existing ones have their `instructions` updated. This
means `python main.py seed` can run safely on every startup and re-applies changes
to the seed file each deploy.

Classifications are **never deleted**. Removing an entry from the seed file leaves
the corresponding row in the database untouched (a classification may still be
referenced by existing meldingen or a form). Remove obsolete classifications
manually via the API (`DELETE /api/v1/classification/{id}`) once nothing references
them.
