## Seed files

This folder stores the seed files used to initialize the database with default or sample data. 
Seed files are stored as JSON and are imported in the `meldingen-entrypoint.sh` script through the Typer Command `python main.py seed` 

Examples of the structure of the seed files can be found in the `examples` folder. 

### Currently supported seed files

| Model          | Seed File Name     |  
|----------------|--------------------| 
| Classification | classifications.json  |  

### Behaviour

Seeding is **idempotent and insert-only**. Classifications are matched by their unique
`name`: entries whose name is not yet in the database are inserted, and entries that
already exist are left completely untouched. This means `python main.py seed` can run
safely on every startup.

Existing classifications are **never updated or deleted**:

- Editing the `instructions` of an already-seeded classification in the file has **no
  effect** — update it via the API (`PATCH /api/v1/classification/{id}`) instead.
- Removing an entry from the file leaves the corresponding row in place (it may still be
  referenced by existing meldingen or a form). Delete it manually via the API
  (`DELETE /api/v1/classification/{id}`) once nothing references it.
