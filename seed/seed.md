## Seed files

This folder stores the seed files used to initialize the database with default or sample data. 
Seed files are stored as JSON and are imported in the `meldingen-entrypoint.sh` script through the Typer Command `python main.py seed` 

Examples of the structure of the seed files can be found in the `examples` folder. 

### Currently supported seed files

| Model          | Seed File Name     |  
|----------------|--------------------| 
| Classification | classifications.json  |  
