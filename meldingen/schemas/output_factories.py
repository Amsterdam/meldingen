from typing import Union

from meldingen.location import LocationOutputTransformer
from meldingen.models import (
    BaseFormIoValuesComponent,
    Form,
    FormIoCheckBoxComponent,
    FormIoComponent,
    FormIoPanelComponent,
    FormIoQuestionComponent,
    FormIoRadioComponent,
    FormIoSelectComponent,
    FormIoSelectComponentData,
    FormIoTextAreaComponent,
    FormIoTextFieldComponent,
    Melding,
    StaticForm,
)
from meldingen.schemas.output import (
    BaseFormComponentOutput,
    FormCheckboxComponentOutput,
    FormComponentOutputValidate,
    FormComponentValueOutput,
    FormOutput,
    FormPanelComponentOutput,
    FormRadioComponentOutput,
    FormSelectComponentDataOutput,
    FormSelectComponentOutput,
    FormTextAreaComponentOutput,
    FormTextFieldInputComponentOutput,
    MeldingOutput,
    SimpleStaticFormOutput,
    StaticFormCheckboxComponentOutput,
    StaticFormOutput,
    StaticFormPanelComponentOutput,
    StaticFormRadioComponentOutput,
    StaticFormSelectComponentOutput,
    StaticFormTextAreaComponentOutput,
    StaticFormTextFieldInputComponentOutput,
)


class ValidateAdder:
    async def __call__(self, component: FormIoQuestionComponent, output: BaseFormComponentOutput) -> None:
        required = await component.awaitable_attrs.required
        if required is None:
            required = False

        jsonlogic = await component.awaitable_attrs.jsonlogic
        if jsonlogic is not None:
            output.validate_ = FormComponentOutputValidate.model_validate_json(
                f'{{"json": {jsonlogic}, "required": {"true" if required else "false"} }}'
            )
        else:
            output.validate_ = FormComponentOutputValidate(required=required)


class StaticFormTextAreaComponentOutputFactory:
    _add_validate: ValidateAdder

    def __init__(self, validate_adder: ValidateAdder):
        self._add_validate = validate_adder

    async def __call__(self, component: FormIoTextAreaComponent) -> StaticFormTextAreaComponentOutput:
        output = StaticFormTextAreaComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            auto_expand=await component.awaitable_attrs.auto_expand,
            max_char_count=component.max_char_count,
            position=component.position,
        )

        await self._add_validate(component, output)

        return output


class StaticFormTextFieldInputComponentOutputFactory:
    _add_validate: ValidateAdder

    def __init__(self, validate_adder: ValidateAdder):
        self._add_validate = validate_adder

    async def __call__(self, component: FormIoTextFieldComponent) -> StaticFormTextFieldInputComponentOutput:
        output = StaticFormTextFieldInputComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            position=component.position,
        )

        await self._add_validate(component, output)

        return output


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
    _add_validate: ValidateAdder

    def __init__(self, values_factory: FormComponentValueOutputFactory, validate_adder: ValidateAdder) -> None:
        self._values = values_factory
        self._add_validate = validate_adder

    async def __call__(self, component: FormIoCheckBoxComponent) -> StaticFormCheckboxComponentOutput:
        output = StaticFormCheckboxComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            position=component.position,
            values=await self._values(component),
        )

        await self._add_validate(component, output)

        return output


class StaticFormRadioComponentOutputFactory:
    _values: FormComponentValueOutputFactory
    _add_validate: ValidateAdder

    def __init__(self, values_factory: FormComponentValueOutputFactory, validate_adder: ValidateAdder) -> None:
        self._values = values_factory
        self._add_validate = validate_adder

    async def __call__(self, component: FormIoRadioComponent) -> StaticFormRadioComponentOutput:
        output = StaticFormRadioComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            position=component.position,
            values=await self._values(component),
        )

        await self._add_validate(component, output)

        return output


class StaticFormSelectComponentOutputFactory:
    _data: FormSelectComponentDataOutputFactory
    _add_validate: ValidateAdder

    def __init__(self, data_factory: FormSelectComponentDataOutputFactory, validate_adder: ValidateAdder) -> None:
        self._data = data_factory
        self._add_validate = validate_adder

    async def __call__(self, component: FormIoSelectComponent) -> StaticFormSelectComponentOutput:
        output = StaticFormSelectComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            position=component.position,
            widget=await component.awaitable_attrs.widget,
            placeholder=component.placeholder,
            data=await self._data(component),
        )

        await self._add_validate(component, output)

        return output


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
            title=await component.awaitable_attrs.title,
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
            id=static_form.id,
            type=str(static_form.type),
            title=static_form.title,
            display=static_form.display,
            components=await self._components(components),
            created_at=static_form.created_at,
            updated_at=static_form.updated_at,
        )


class SimpleStaticFormOutputFactory:
    async def __call__(self, static_form: StaticForm) -> SimpleStaticFormOutput:
        return SimpleStaticFormOutput(
            id=static_form.id,
            type=str(static_form.type),
            title=static_form.title,
            display=static_form.display,
            created_at=static_form.created_at,
            updated_at=static_form.updated_at,
        )


class FormTextAreaComponentOutputFactory:
    _add_validate: ValidateAdder

    def __init__(self, validate_adder: ValidateAdder):
        self._add_validate = validate_adder

    async def __call__(self, component: FormIoTextAreaComponent) -> FormTextAreaComponentOutput:
        question = await component.awaitable_attrs.question

        output = FormTextAreaComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            auto_expand=component.auto_expand,
            max_char_count=component.max_char_count,
            position=component.position,
            question=question.id,
        )

        await self._add_validate(component, output)

        return output


class FormTextFieldInputComponentOutputFactory:
    _add_validate: ValidateAdder

    def __init__(self, validate_adder: ValidateAdder):
        self._add_validate = validate_adder

    async def __call__(self, component: FormIoTextFieldComponent) -> FormTextFieldInputComponentOutput:
        question = await component.awaitable_attrs.question

        output = FormTextFieldInputComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            position=component.position,
            question=question.id,
        )

        await self._add_validate(component, output)

        return output


class FormCheckboxComponentOutputFactory:
    _values: FormComponentValueOutputFactory
    _add_validate: ValidateAdder

    def __init__(self, values_factory: FormComponentValueOutputFactory, validate_adder: ValidateAdder):
        self._values = values_factory
        self._add_validate = validate_adder

    async def __call__(self, component: FormIoCheckBoxComponent) -> FormCheckboxComponentOutput:
        question = await component.awaitable_attrs.question

        output = FormCheckboxComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            position=component.position,
            values=await self._values(component),
            question=question.id,
        )

        await self._add_validate(component, output)

        return output


class FormRadioComponentOutputFactory:
    _values: FormComponentValueOutputFactory
    _add_validate: ValidateAdder

    def __init__(self, values_factory: FormComponentValueOutputFactory, validate_adder: ValidateAdder):
        self._values = values_factory
        self._add_validate = validate_adder

    async def __call__(self, component: FormIoRadioComponent) -> FormRadioComponentOutput:
        question = await component.awaitable_attrs.question

        output = FormRadioComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            position=component.position,
            values=await self._values(component),
            question=question.id,
        )

        await self._add_validate(component, output)

        return output


class FormSelectComponentOutputFactory:
    _data: FormSelectComponentDataOutputFactory
    _add_validate: ValidateAdder

    def __init__(self, data_factory: FormSelectComponentDataOutputFactory, validate_adder: ValidateAdder):
        self._data = data_factory
        self._add_validate = validate_adder

    async def __call__(self, component: FormIoSelectComponent) -> FormSelectComponentOutput:
        question = await component.awaitable_attrs.question

        output = FormSelectComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            position=component.position,
            widget=component.widget,
            placeholder=component.placeholder,
            data=await self._data(component),
            question=question.id,
        )

        await self._add_validate(component, output)

        return output


class FormComponentOutputFactory:
    _text_area_component: FormTextAreaComponentOutputFactory
    _text_field_component: FormTextFieldInputComponentOutputFactory
    _checkbox_component: FormCheckboxComponentOutputFactory
    _radio_component: FormRadioComponentOutputFactory
    _select_component: FormSelectComponentOutputFactory

    def __init__(
        self,
        text_area_factory: FormTextAreaComponentOutputFactory,
        text_field_factory: FormTextFieldInputComponentOutputFactory,
        checkbox_factory: FormCheckboxComponentOutputFactory,
        radio_factory: FormRadioComponentOutputFactory,
        select_factory: FormSelectComponentOutputFactory,
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
            FormSelectComponentOutput,
        ]
    ]:
        output_components: list[
            Union[
                FormPanelComponentOutput,
                FormTextAreaComponentOutput,
                FormTextFieldInputComponentOutput,
                FormCheckboxComponentOutput,
                FormRadioComponentOutput,
                FormSelectComponentOutput,
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
            title=await component.awaitable_attrs.title,
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


class MeldingOutputFactory:
    _transform_location: LocationOutputTransformer

    def __init__(self, location_transformer: LocationOutputTransformer):
        self._transform_location = location_transformer

    def __call__(self, melding: Melding) -> MeldingOutput:
        if melding.geo_location is None:
            geojson = None
        else:
            geojson = self._transform_location(melding.geo_location)

        return MeldingOutput(
            id=melding.id,
            text=melding.text,
            state=melding.state,
            classification=melding.classification_id,
            created_at=melding.created_at,
            updated_at=melding.updated_at,
            geo_location=geojson,
            email=melding.email,
            phone=melding.phone,
        )
