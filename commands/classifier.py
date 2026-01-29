import asyncio
import typer
from rich import print

from meldingen.classification import OpenAIClassifierAdapter
from meldingen.config import settings
from meldingen.repositories import ClassificationRepository
from meldingen.dependencies import database_engine, database_session, DatabaseSessionManager
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai import Agent
from pydantic import Field
from typing import Literal
from pydantic import BaseModel

app = typer.Typer()

# Use the same make_classification_model as in dependencies.py

def make_classification_model(classifications_list):
    annotations = {"classification": Literal[tuple(classifications_list)]}
    namespace = {"__annotations__": annotations, "classification": Field(..., description="The chosen classification")}
    return type("ClassificationResponse", (BaseModel,), namespace)

@app.command()
def classify(text: str):
    """Classify the given text using the OpenAIClassifierAdapter and real agent."""
    async def classify_async():
        # Setup DB session
        engine = database_engine()
        async for session in database_session(DatabaseSessionManager(engine)):
            repository = ClassificationRepository(session)
            classifications_list = [c.name for c in await repository.list()]
            ClassificationModel = make_classification_model(classifications_list)
            model = OpenAIChatModel(
                settings.llm_model_identifier,
                provider=OpenAIProvider(base_url=settings.llm_base_url)
            )
            system_prompt = (
                f"You are a classifier of text. "
                f"Choose one of the following classifications: {', '.join(classifications_list)}."
            )
            agent = Agent(model, system_prompt=system_prompt, output_type=ClassificationModel)
            adapter = OpenAIClassifierAdapter(agent=agent)
            result = await adapter(text)
            print(f"[green]Classification:[/green] {result}")
            break
    asyncio.run(classify_async())

if __name__ == "__main__":
    app()
