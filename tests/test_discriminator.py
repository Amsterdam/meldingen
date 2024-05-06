from typing import Any

import pytest

from meldingen.schemas import component_discriminator


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "value, match_value",
    [
        ({"type": "panel"}, "panel"),
        ({"type": "textArea"}, "component"),
        ({"type": "not-a-panel"}, "component"),
        ("not-a-dict-returns-none", None),
        (True, None),
        (1000, None),
        (["type", "panel"], None),
    ],
)
async def test_component_discriminator(value: Any, match_value: Any) -> None:
    result = component_discriminator(value)

    assert result == match_value
