from typing import Union

from meldingen.models import (
    BaseFormIoValuesComponent,
    Form,
    FormIoCheckBoxComponent,
    FormIoComponent,
    FormIoPanelComponent,
    FormIoRadioComponent,
    FormIoSelectComponent,
    FormIoSelectComponentData,
    FormIoTextAreaComponent,
    FormIoTextFieldComponent,
    StaticForm,
)
from meldingen.output_schemas import (
    FormCheckboxComponentOutput,
    FormComponentValueOutput,
    FormOutput,
    FormPanelComponentOutput,
    FormRadioComponentOutput,
    FormSelectComponentDataOutput,
    FormSelectComponentOutput,
    FormTextAreaComponentOutput,
    FormTextFieldInputComponentOutput,
    StaticFormCheckboxComponentOutput,
    StaticFormOutput,
    StaticFormPanelComponentOutput,
    StaticFormRadioComponentOutput,
    StaticFormSelectComponentOutput,
    StaticFormTextAreaComponentOutput,
    StaticFormTextFieldInputComponentOutput,
)


class StaticFormTextAreaComponentOutputFactory:
    async def __call__(self, component: FormIoTextAreaComponent) -> StaticFormTextAreaComponentOutput:
        return StaticFormTextAreaComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            auto_expand=await component.awaitable_attrs.auto_expand,
            show_char_count=component.show_char_count,
            position=component.position,
        )


class StaticFormTextFieldInputComponentOutputFactory:
    async def __call__(self, component: FormIoTextFieldComponent) -> StaticFormTextFieldInputComponentOutput:
        return StaticFormTextFieldInputComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            position=component.position,
        )


class FormComponentValueOutputFactory:
    async def __call__(
        self, component: BaseFormIoValuesComponent | FormIoSelectComponentData
    ) -> list[FormComponentValueOutput]:
        return [
            FormComponentValueOutput(label=value.label, value=value.value, position=value.position)
            for value in await component.awaitable_attrs.values
        ]


class FormSelectComponentDataOutputFactory:
    _values: FormComponentValueOutputFactory

    def __init__(self, values_factory: FormComponentValueOutputFactory):
        self._values = values_factory

    async def __call__(self, component: FormIoSelectComponent) -> FormSelectComponentDataOutput:
        return FormSelectComponentDataOutput(values=await self._values(await component.awaitable_attrs.data))


class StaticFormCheckboxComponentOutputFactory:
    _values: FormComponentValueOutputFactory

    def __init__(self, values_factory: FormComponentValueOutputFactory) -> None:
        self._values = values_factory

    async def __call__(self, component: FormIoCheckBoxComponent) -> StaticFormCheckboxComponentOutput:
        return StaticFormCheckboxComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            position=component.position,
            values=await self._values(component),
        )


class StaticFormRadioComponentOutputFactory:
    _values: FormComponentValueOutputFactory

    def __init__(self, values_factory: FormComponentValueOutputFactory) -> None:
        self._values = values_factory

    async def __call__(self, component: FormIoRadioComponent) -> StaticFormRadioComponentOutput:
        return StaticFormRadioComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            position=component.position,
            values=await self._values(component),
        )


class StaticFormSelectComponentOutputFactory:
    _data: FormSelectComponentDataOutputFactory

    def __init__(self, data_factory: FormSelectComponentDataOutputFactory):
        self._data = data_factory

    async def __call__(self, component: FormIoSelectComponent) -> StaticFormSelectComponentOutput:
        return StaticFormSelectComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            position=component.position,
            data=await self._data(component),
        )


class StaticFormComponentOutputFactory:
    _text_area_component: StaticFormTextAreaComponentOutputFactory
    _text_field_component: StaticFormTextFieldInputComponentOutputFactory
    _checkbox_component: StaticFormCheckboxComponentOutputFactory
    _radio_component: StaticFormRadioComponentOutputFactory
    _select_component: StaticFormSelectComponentOutputFactory

    def __init__(
        self,
        text_area_factory: StaticFormTextAreaComponentOutputFactory,
        text_field_factory: StaticFormTextFieldInputComponentOutputFactory,
        checkbox_factory: StaticFormCheckboxComponentOutputFactory,
        radio_factory: StaticFormRadioComponentOutputFactory,
        select_factory: StaticFormSelectComponentOutputFactory,
    ):
        self._text_area_component = text_area_factory
        self._text_field_component = text_field_factory
        self._checkbox_component = checkbox_factory
        self._radio_component = radio_factory
        self._select_component = select_factory

    async def __call__(self, components: list[FormIoComponent]) -> list[
        Union[
            StaticFormPanelComponentOutput,
            StaticFormTextAreaComponentOutput,
            StaticFormTextFieldInputComponentOutput,
            StaticFormCheckboxComponentOutput,
            StaticFormRadioComponentOutput,
            StaticFormSelectComponentOutput,
        ]
    ]:
        output_components: list[
            Union[
                StaticFormPanelComponentOutput,
                StaticFormTextAreaComponentOutput,
                StaticFormTextFieldInputComponentOutput,
                StaticFormCheckboxComponentOutput,
                StaticFormRadioComponentOutput,
                StaticFormSelectComponentOutput,
            ]
        ] = []
        for component in components:
            if isinstance(component, FormIoPanelComponent):
                output_components.append(await self._panel_component(component))
            elif isinstance(component, FormIoTextAreaComponent):
                output_components.append(await self._text_area_component(component))
            elif isinstance(component, FormIoTextFieldComponent):
                output_components.append(await self._text_field_component(component))
            elif isinstance(component, FormIoCheckBoxComponent):
                output_components.append(await self._checkbox_component(component))
            elif isinstance(component, FormIoRadioComponent):
                output_components.append(await self._radio_component(component))
            elif isinstance(component, FormIoSelectComponent):
                output_components.append(await self._select_component(component))

        return output_components

    async def _panel_component(self, component: FormIoPanelComponent) -> StaticFormPanelComponentOutput:
        children = await component.awaitable_attrs.components
        children_output = await self.__call__(children)

        return StaticFormPanelComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            position=component.position,
            components=children_output,
        )


class StaticFormOutputFactory:
    _components: StaticFormComponentOutputFactory

    def __init__(self, components_factory: StaticFormComponentOutputFactory) -> None:
        self._components = components_factory

    async def __call__(self, static_form: StaticForm) -> StaticFormOutput:
        components = await static_form.awaitable_attrs.components

        return StaticFormOutput(
            type=str(static_form.type),
            title=static_form.title,
            display=static_form.display,
            components=await self._components(components),
            created_at=static_form.created_at,
            updated_at=static_form.updated_at,
        )


class FormTextAreaComponentOutputFactory:
    async def __call__(self, component: FormIoTextAreaComponent) -> FormTextAreaComponentOutput:
        question = await component.awaitable_attrs.question

        return FormTextAreaComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            auto_expand=component.auto_expand,
            show_char_count=component.show_char_count,
            position=component.position,
            question=question.id,
        )


class FormTextFieldInputComponentOutputFactory:
    async def __call__(self, component: FormIoTextFieldComponent) -> FormTextFieldInputComponentOutput:
        question = await component.awaitable_attrs.question

        return FormTextFieldInputComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            position=component.position,
            question=question.id,
        )


class FormCheckboxComponentOutputFactory:
    _values: FormComponentValueOutputFactory

    def __init__(self, values_factory: FormComponentValueOutputFactory):
        self._values = values_factory

    async def __call__(self, component: FormIoCheckBoxComponent) -> FormCheckboxComponentOutput:
        question = await component.awaitable_attrs.question

        return FormCheckboxComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            position=component.position,
            values=await self._values(component),
            question=question.id,
        )


class FormRadioComponentOutputFactory:
    _values: FormComponentValueOutputFactory

    def __init__(self, values_factory: FormComponentValueOutputFactory):
        self._values = values_factory

    async def __call__(self, component: FormIoRadioComponent) -> FormRadioComponentOutput:
        question = await component.awaitable_attrs.question

        return FormRadioComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            position=component.position,
            values=await self._values(component),
            question=question.id,
        )


class FormSelectComponentOutputFactory:
    _data: FormSelectComponentDataOutputFactory

    def __init__(self, data_factory: FormSelectComponentDataOutputFactory):
        self._data = data_factory

    async def __call__(self, component: FormIoSelectComponent) -> FormSelectComponentOutput:
        question = await component.awaitable_attrs.question

        return FormSelectComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            position=component.position,
            data=await self._data(component),
            question=question.id,
        )


class FormComponentOutputFactory:
    _text_area_component: FormTextAreaComponentOutputFactory
    _text_field_component: FormTextFieldInputComponentOutputFactory
    _checkbox_component: FormCheckboxComponentOutputFactory
    _radio_component: FormRadioComponentOutputFactory
    _select_component: FormSelectComponentDataOutputFactory

    def __init__(
        self,
        text_area_factory: FormTextAreaComponentOutputFactory,
        text_field_factory: FormTextFieldInputComponentOutputFactory,
        checkbox_factory: FormCheckboxComponentOutputFactory,
        radio_factory: FormRadioComponentOutputFactory,
        select_factory: FormSelectComponentDataOutputFactory,
    ):
        self._text_area_component = text_area_factory
        self._text_field_component = text_field_factory
        self._checkbox_component = checkbox_factory
        self._radio_component = radio_factory
        self._select_component = select_factory

    async def __call__(self, components: list[FormIoComponent]) -> list[
        Union[
            FormPanelComponentOutput,
            FormTextAreaComponentOutput,
            FormTextFieldInputComponentOutput,
            FormCheckboxComponentOutput,
            FormRadioComponentOutput,
            FormSelectComponentDataOutput,
        ]
    ]:
        output_components: list[
            Union[
                FormPanelComponentOutput,
                FormTextAreaComponentOutput,
                FormTextFieldInputComponentOutput,
                FormCheckboxComponentOutput,
                FormRadioComponentOutput,
                FormSelectComponentDataOutput,
            ]
        ] = []
        for component in components:
            if isinstance(component, FormIoPanelComponent):
                output_components.append(await self._panel_component(component))
            elif isinstance(component, FormIoTextAreaComponent):
                output_components.append(await self._text_area_component(component))
            elif isinstance(component, FormIoTextFieldComponent):
                output_components.append(await self._text_field_component(component))
            elif isinstance(component, FormIoCheckBoxComponent):
                output_components.append(await self._checkbox_component(component))
            elif isinstance(component, FormIoRadioComponent):
                output_components.append(await self._radio_component(component))
            elif isinstance(component, FormIoSelectComponent):
                output_components.append(await self._select_component(component))

        return output_components

    async def _panel_component(self, component: FormIoPanelComponent) -> FormPanelComponentOutput:
        children = await component.awaitable_attrs.components
        children_output = await self.__call__(children)

        return FormPanelComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            position=component.position,
            components=children_output,
        )


class FormOutputFactory:
    _components: FormComponentOutputFactory

    def __init__(self, components_factory: FormComponentOutputFactory):
        self._components = components_factory

    async def __call__(self, form: Form) -> FormOutput:
        components = await form.awaitable_attrs.components
        classification = await form.awaitable_attrs.classification

        return FormOutput(
            id=form.id,
            title=form.title,
            display=form.display,
            classification=classification.id if classification else None,
            components=await self._components(components),
            created_at=form.created_at,
            updated_at=form.updated_at,
        )
