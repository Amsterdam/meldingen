from unittest.mock import AsyncMock, Mock

import pytest

from meldingen.classification import build_classification_prompt, build_dynamic_classification_response_model
from meldingen.repositories import ClassificationRepository


def _make_classification(name: str, instructions: str | None = None) -> Mock:
    c = Mock()
    c.name = name
    c.instructions = instructions
    return c


@pytest.mark.anyio
async def test_build_classification_prompt_with_instructions() -> None:
    repository = Mock(ClassificationRepository)
    repository.list = AsyncMock(
        return_value=[
            _make_classification("Zwerfvuil", "Meldingen over rondslingerend afval"),
            _make_classification("Straatverlichting", "Kapotte of niet werkende lantaarns"),
        ]
    )

    prompt = await build_classification_prompt(repository)

    assert "- Zwerfvuil: Meldingen over rondslingerend afval" in prompt
    assert "- Straatverlichting: Kapotte of niet werkende lantaarns" in prompt


@pytest.mark.anyio
async def test_build_classification_prompt_without_instructions() -> None:
    repository = Mock(ClassificationRepository)
    repository.list = AsyncMock(
        return_value=[
            _make_classification("Groenvoorziening"),
        ]
    )

    prompt = await build_classification_prompt(repository)

    assert "- Groenvoorziening" in prompt
    assert "- Groenvoorziening:" not in prompt


@pytest.mark.anyio
async def test_build_classification_prompt_mixed() -> None:
    repository = Mock(ClassificationRepository)
    repository.list = AsyncMock(
        return_value=[
            _make_classification("Zwerfvuil", "Rondslingerend afval"),
            _make_classification("Groenvoorziening"),
        ]
    )

    prompt = await build_classification_prompt(repository)

    assert "- Zwerfvuil: Rondslingerend afval" in prompt
    assert "- Groenvoorziening" in prompt
    assert "- Groenvoorziening:" not in prompt


@pytest.mark.anyio
async def test_build_dynamic_classification_response_model_accepts_valid_name() -> None:
    repository = Mock(ClassificationRepository)
    repository.list = AsyncMock(
        return_value=[
            _make_classification("Zwerfvuil"),
            _make_classification("Straatverlichting"),
        ]
    )

    model = await build_dynamic_classification_response_model(repository)
    instance = model(classification="Zwerfvuil")

    assert instance.classification == "Zwerfvuil"


@pytest.mark.anyio
async def test_build_dynamic_classification_response_model_rejects_invalid_name() -> None:
    repository = Mock(ClassificationRepository)
    repository.list = AsyncMock(
        return_value=[
            _make_classification("Zwerfvuil"),
            _make_classification("Straatverlichting"),
        ]
    )

    model = await build_dynamic_classification_response_model(repository)

    with pytest.raises(Exception):
        model(classification="Onbekend")
