# Testing and Linting

To ensure code quality and reliability, it is essential that all linting 
checks and tests pass before pushing code changes. This section outlines how 
to run testing and linting locally for the Meldingen application.

## PyTest

PyTest is used for running tests within the Meldingen application. To execute 
PyTest, run the following command:

```bash
docker-compose run --rm meldingen pytest --test-alembic -v
```

This command runs PyTest within the Meldingen container, executing tests while 
providing verbose output.

## Black

Black is a code formatter for Python. To check if the code complies with Black 
formatting standards, run the following command:

```bash
docker-compose run --rm meldingen poetry run black . --check
```

This command checks whether the code in the project directory conforms to 
Black's formatting rules without actually modifying the files.

## iSort

iSort is used for sorting Python imports. To ensure proper import sorting 
within the Meldingen application, execute the following command:

```bash
docker-compose run --rm meldingen poetry run isort .
```

This command sorts the imports in Python files in the project directory 
according to the specified rules.

## MyPy

MyPy is a static type checker for Python. To perform strict type checking 
across the Meldingen application, use the following command:

```bash
docker-compose run --rm meldingen poetry run mypy --strict .
```

This command runs MyPy with strict mode enabled, checking Python files in the 
project directory for type errors.