from meldingen.models import (
    Form,
    FormIoCheckBoxComponent,
    FormIoComponent,
    FormIoPanelComponent,
    FormIoQuestionComponent,
    FormIoRadioComponent,
    StaticForm,
)
from meldingen.schemas import (
    FormComponentOutput,
    FormComponentValueOutput,
    FormOutput,
    FormPanelComponentOutput,
    StaticFormOutput,
)


class BaseFormOutPutRenderer:
    async def _render_panel_component(self, component: FormIoPanelComponent) -> FormPanelComponentOutput:
        components = await component.awaitable_attrs.components
        panel_components = await self._render_components(components)

        return FormPanelComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            auto_expand=component.auto_expand,
            show_char_count=component.show_char_count,
            position=component.position,
            components=panel_components,
        )

    async def _render_non_panel_component(
        self, component: FormIoQuestionComponent | FormIoRadioComponent | FormIoCheckBoxComponent
    ) -> FormComponentOutput:
        output = FormComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            auto_expand=component.auto_expand,
            show_char_count=component.show_char_count,
            position=component.position,
            question=await component.awaitable_attrs.question_id,
        )

        if isinstance(component, (FormIoRadioComponent, FormIoCheckBoxComponent)):
            c_values = await component.awaitable_attrs.values
            if len(c_values):
                values: list[FormComponentValueOutput] = [
                    FormComponentValueOutput(label=v.label, value=v.value, position=v.position) for v in c_values
                ]
                output.values = values

        return output

    async def _render_components(
        self, components: list[FormIoPanelComponent | FormIoComponent]
    ) -> list[FormPanelComponentOutput | FormComponentOutput]:
        output: list[FormComponentOutput | FormPanelComponentOutput] = []
        for component in components:
            if isinstance(component, FormIoPanelComponent):
                output.append(await self._render_panel_component(component))
            elif isinstance(component, FormIoQuestionComponent):
                output.append(await self._render_non_panel_component(component))
        return output


class FormOutPutRenderer(BaseFormOutPutRenderer):
    async def __call__(self, form: Form) -> FormOutput:
        components = await form.awaitable_attrs.components
        components_output = await self._render_components(components)

        return FormOutput(
            id=form.id,
            title=form.title,
            display=form.display,
            components=components_output,
            classification=form.classification_id,
            created_at=form.created_at,
            updated_at=form.updated_at,
        )


class StaticFormOutPutRenderer(BaseFormOutPutRenderer):
    async def __call__(self, form: StaticForm) -> StaticFormOutput:
        components = await form.awaitable_attrs.components
        components_output = await self._render_components(components)

        return StaticFormOutput(
            type=form.type,
            title=form.title,
            display=form.display,
            components=components_output,
            created_at=form.created_at,
            updated_at=form.updated_at,
        )
