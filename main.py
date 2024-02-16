import asyncio

import typer

from async_casbin_sqlmodel_adapter.models import CasbinRule
from meldingen.config import Settings
from meldingen.containers import Container
from meldingen.models import Group, User, UserInput

app = typer.Typer()
container = Container()
container.settings.from_dict(Settings().model_dump())


async def async_add_user(email: str) -> None:
    user_repository = await container.user_repository()

    user_input = UserInput(username=email, email=email)
    user = User(**user_input.model_dump())

    await user_repository.save(user)


@app.command()
def add_user(email: str) -> None:
    asyncio.run(async_add_user(email))


async def async_add_group(name: str) -> None:
    group_repository = await container.group_repository()

    await group_repository.save(Group(name=name))


@app.command()
def add_group(name: str) -> None:
    asyncio.run(async_add_group(name))


async def async_add_user_to_group(email: str, group_name: str) -> None:
    user_repository = await container.user_repository()
    group_repository = await container.group_repository()

    user = await user_repository.find_by_email(email)
    group = await group_repository.find_by_name(group_name)

    user.groups.append(group)

    await user_repository.save(user)


@app.command()
def add_user_to_group(email: str, group_name: str) -> None:
    asyncio.run(async_add_user_to_group(email, group_name))


async def async_add_casbin_rules() -> None:
    db_session = await container.database_session()
    db_session.add(CasbinRule(ptype="p", v0="admins", v1="user", v2="create"))
    db_session.add(CasbinRule(ptype="p", v0="admins", v1="user", v2="list"))
    db_session.add(CasbinRule(ptype="p", v0="admins", v1="user", v2="retrieve"))
    db_session.add(CasbinRule(ptype="p", v0="admins", v1="user", v2="update"))
    db_session.add(CasbinRule(ptype="p", v0="admins", v1="user", v2="delete"))

    await db_session.commit()


@app.command()
def add_casbin_rules() -> None:
    asyncio.run(async_add_casbin_rules())


if __name__ == "__main__":
    app()
