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

## LLM classification evaluation

There is an **opt-in** test suite that evaluates the current LLM classification behavior against a dataset of example melding teksten.

To run it, set `LLM_EVAL=1` and run only the `llm`-marked tests:

```bash
docker compose run --rm \
	-e LLM_EVAL=1 \
	-e API_LLM_ENABLED=true \
	-e API_LLM_PROVIDER=azure \
	-e LLM_URL='https://<your-azure-openai-endpoint>' \
	-e LLM_MODEL='<your-deployment-name>' \
	-e API_LLM_API_KEY='<optional-if-not-using-managed-identity>' \
	meldingen pytest -q -m llm
```

Data inputs:

- **Classifications (names + instructions)**: set `LLM_EVAL_CLASSIFICATIONS_PATH` (defaults to `seed/examples/classifications.json`).
- **Evaluation cases**: set `LLM_EVAL_DATASET_PATH` (defaults to `tests/fixtures/llm_classification_cases.jsonl`).

## Black

Black is a code formatter for Python. To check if the code complies with Black 
formatting standards, run the following command:

```bash
docker compose run --rm meldingen uv run black . --check
```

This command checks whether the code in the project directory conforms to 
Black's formatting rules without actually modifying the files.

## iSort

iSort is used for sorting Python imports. To ensure proper import sorting 
within the Meldingen application, execute the following command:

```bash
docker compose run --rm meldingen uv run isort .
```

This command sorts the imports in Python files in the project directory 
according to the specified rules.

## MyPy

MyPy is a static type checker for Python. To perform strict type checking 
across the Meldingen application, use the following command:

```bash
docker compose run --rm meldingen bash -c 'uv run mypy --strict . | uv run mypy-baseline filter'
```

This command runs MyPy with strict mode enabled, checking Python files in the 
project directory for type errors.