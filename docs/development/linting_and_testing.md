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

There is an **opt-in** test suite at `tests/llm_eval/` that evaluates the current LLM classification behavior against a fixed dataset of example melding teksten. It exercises the real `AgentClassifierAdapter` (same prompt, same agent wiring as production), but swaps the database-backed `ClassificationRepository` for a mock that returns the categories defined in the dataset file, so the suite is reproducible and version-controlled.

Every test in the suite is decorated with `@pytest.mark.llm_eval`, and `pyproject.toml` sets `addopts = "-m 'not llm_eval'"` so the default `pytest` run skips it. To run it, override the marker filter on the command line and provide the LLM environment variables:

```bash
docker compose run --rm \
	-e API_LLM_ENABLED=true \
	-e API_LLM_PROVIDER=azure \
	-e LLM_URL='https://<your-azure-openai-endpoint>' \
	-e LLM_MODEL='<your-deployment-name>' \
	-e API_LLM_API_KEY='<optional-if-not-using-managed-identity>' \
	meldingen pytest tests/llm_eval/ -m llm_eval -v
```

The `-m llm_eval` flag is required: it overrides the default `-m 'not llm_eval'` from `pyproject.toml`, otherwise pytest would still filter the suite out even with the path specified.

If `API_LLM_ENABLED` is unset or false, every test in the suite is skipped with an explanatory message.

**Dataset:** all classifications and evaluation cases live in a single JSON file at [`tests/llm_eval/test_cases.json`](../../tests/llm_eval/test_cases.json). Edit that file directly to add categories or new test cases — no code changes needed. Each test case becomes a separate parametrized pytest invocation.

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