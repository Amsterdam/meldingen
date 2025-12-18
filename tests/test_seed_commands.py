import pytest
from _pytest.capture import CaptureFixture

from commands.seed import async_seed_classification_from_file

EXAMPLE_FILE_PATH = "./seed/examples/classifications.json"


@pytest.mark.anyio
async def test_seed_classifications(capsys: CaptureFixture[str]) -> None:
    await async_seed_classification_from_file(EXAMPLE_FILE_PATH, dry_run=True)
    captured = capsys.readouterr()
    assert f"🟢 - Dry run - would have seeded 3 classifications from \n{EXAMPLE_FILE_PATH}." in captured.out
