import asyncio

import typer
from rich import print

from meldingen.dependencies import azure_container_client

app = typer.Typer()


async def async_create_container() -> None:
    async for client in azure_container_client():
        if not await client.exists():
            await client.create_container()

            print("[green]Success[/green] Azure storage blobs container created!")
        else:
            print("[yellow]Warning[/yellow] Azure storage blobs container already exists!")


@app.command()
def create_container() -> None:
    asyncio.run(async_create_container())


if __name__ == "__main__":
    app()
