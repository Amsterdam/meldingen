from datetime import datetime
from typing import Union

from pydantic import AliasGenerator, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

### Form.io ###


class BaseFormOutput(BaseModel):
    id: int
    title: str
    display: str
    created_at: datetime
    updated_at: datetime


class SimpleStaticFormOutput(BaseModel):
    type: str
    title: str
    display: str
    created_at: datetime
    updated_at: datetime


class StaticFormOutput(SimpleStaticFormOutput):
    components: list[
        Union[
            "StaticFormPanelComponentOutput",
            "StaticFormTextAreaComponentOutput",
            "StaticFormTextFieldInputComponentOutput",
            "StaticFormCheckboxComponentOutput",
            "StaticFormRadioComponentOutput",
            "StaticFormSelectComponentOutput",
        ]
    ]


class SimpleFormOutput(BaseFormOutput):
    id: int
    classification: int | None = None


class FormOutput(SimpleFormOutput):
    components: list[
        Union[
            "FormPanelComponentOutput",
            "FormTextAreaComponentOutput",
            "FormTextFieldInputComponentOutput",
            "FormCheckboxComponentOutput",
            "FormRadioComponentOutput",
            "FormSelectComponentOutput",
        ]
    ]


class BaseFormPanelComponentOutput(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(serialization_alias=to_camel))

    label: str

    key: str
    type: str
    input: bool

    position: int


class StaticFormPanelComponentOutput(BaseFormPanelComponentOutput):
    components: list[
        Union[
            "StaticFormTextAreaComponentOutput",
            "StaticFormTextFieldInputComponentOutput",
            "StaticFormCheckboxComponentOutput",
            "StaticFormRadioComponentOutput",
        ]
    ]


class FormPanelComponentOutput(BaseFormPanelComponentOutput):
    components: list[
        Union[
            "FormTextAreaComponentOutput",
            "FormTextFieldInputComponentOutput",
            "FormCheckboxComponentOutput",
            "FormRadioComponentOutput",
            "FormSelectComponentOutput",
        ]
    ]


class BaseFormComponentOutput(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(serialization_alias=to_camel))

    label: str
    description: str

    key: str
    type: str
    input: bool

    position: int


class StaticFormTextAreaComponentOutput(BaseFormComponentOutput):
    auto_expand: bool
    show_char_count: bool


class StaticFormTextFieldInputComponentOutput(BaseFormComponentOutput): ...


class StaticFormCheckboxComponentOutput(BaseFormComponentOutput):
    values: list["FormComponentValueOutput"]


class StaticFormRadioComponentOutput(BaseFormComponentOutput):
    values: list["FormComponentValueOutput"]


class FormComponentValueOutput(BaseModel):
    label: str
    value: str
    position: int


class FormSelectComponentDataOutput(BaseModel):
    values: list[FormComponentValueOutput]


class StaticFormSelectComponentOutput(BaseFormComponentOutput):
    data: FormSelectComponentDataOutput


class FormTextAreaComponentOutput(StaticFormTextAreaComponentOutput):
    question: int


class FormTextFieldInputComponentOutput(StaticFormTextFieldInputComponentOutput):
    question: int


class FormCheckboxComponentOutput(StaticFormCheckboxComponentOutput):
    question: int


class FormRadioComponentOutput(StaticFormRadioComponentOutput):
    question: int


class FormSelectComponentOutput(StaticFormSelectComponentOutput):
    question: int
