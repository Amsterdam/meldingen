# import asyncio
#
# import typer
# from rich import print
#
# from meldingen.config import Settings
# from meldingen.containers import Container
# from meldingen.models import Group
#
# app = typer.Typer()
# container = Container()
# container.settings.from_dict(Settings().model_dump())
#
#
# async def async_add_group(name: str) -> None:
#     group_repository = await container.group_repository()
#
#     await group_repository.save(Group(name=name))
#
#     print(f'[green]Success[/green] - Group "{name}" created!')
#
#
# @app.command()
# def add(name: str) -> None:
#     asyncio.run(async_add_group(name))
#
#
# if __name__ == "__main__":
#     app()
