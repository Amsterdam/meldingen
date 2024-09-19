from typing import Any

import pytest

from meldingen.models import FormIoComponentTypeEnum
from meldingen.schemas import (
    FormCheckboxComponentInput,
    FormPanelComponentInput,
    FormRadioComponentInput,
    FormSelectComponentInput,
    FormTextAreaComponentInput,
    FormTextFieldComponentInput,
    component_discriminator,
)


@pytest.mark.parametrize(
    "value, match_value",
    [
        ({"type": "panel"}, "panel"),
        ({"type": "textArea"}, "textArea"),
        ({"type": "not-a-panel"}, "not-a-panel"),
        ("not-a-dict-returns-none", None),
        (True, None),
        (1000, None),
        (["type", "panel"], None),
    ],
)
def test_component_discriminator_dict(value: Any, match_value: Any) -> None:
    result = component_discriminator(value)

    assert result == match_value


def test_component_discriminator_panel() -> None:
    result = component_discriminator(FormPanelComponentInput(label="abc", key="abc", components=[]))

    assert result == FormIoComponentTypeEnum.panel


def test_component_discriminator_textarea() -> None:
    result = component_discriminator(
        FormTextAreaComponentInput(
            label="abc", key="abc", description="abc", input=True, autoExpand=True, maxCharCount=255
        )
    )

    assert result == FormIoComponentTypeEnum.text_area


def test_component_discriminator_textfield() -> None:
    result = component_discriminator(FormTextFieldComponentInput(label="abc", description="abc", key="abc", input=True))

    assert result == FormIoComponentTypeEnum.text_field


def test_component_discriminator_radio() -> None:
    result = component_discriminator(
        FormRadioComponentInput(label="abc", description="abc", key="abc", input=True, values=[])
    )

    assert result == FormIoComponentTypeEnum.radio


def test_component_discriminator_checkbox() -> None:
    result = component_discriminator(
        FormCheckboxComponentInput(label="abc", description="abc", key="abc", input=True, values=[])
    )

    assert result == FormIoComponentTypeEnum.checkbox


def test_component_discriminator_select() -> None:
    result = component_discriminator(
        FormSelectComponentInput(
            label="abc", description="abc", key="abc", input=True, widget="html5", placeholder="", data={"values": []}
        )
    )

    assert result == FormIoComponentTypeEnum.select
