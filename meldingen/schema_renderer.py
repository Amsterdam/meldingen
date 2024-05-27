from meldingen.models import Form, FormIoComponent, FormIoPanelComponent
from meldingen.schemas import FormComponentOutput, FormOutput, FormPanelComponentOutput


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

    async def _render_non_panel_component(self, component: FormIoComponent) -> FormComponentOutput:
        return FormComponentOutput(
            label=component.label,
            description=component.description,
            key=component.key,
            type=component.type,
            input=component.input,
            auto_expand=component.auto_expand,
            show_char_count=component.show_char_count,
            position=component.position,
            question=component.question_id,
        )

    async def _render_components(
        self, components: list[FormIoPanelComponent | FormIoComponent]
    ) -> list[FormPanelComponentOutput | FormComponentOutput]:
        output: list[FormComponentOutput | FormPanelComponentOutput] = []
        for component in components:
            if isinstance(component, FormIoPanelComponent):
                output.append(await self._render_panel_component(component))
            else:
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
