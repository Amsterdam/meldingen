from meldingen_core.actions.user import UserCreateAction as BaseUserCreateAction
from meldingen_core.actions.user import UserDeleteAction as BaseUserDeleteAction
from meldingen_core.actions.user import UserListAction as BaseUserListAction
from meldingen_core.actions.user import UserRetrieveAction as BaseUserRetrieveAction
from meldingen_core.actions.user import UserUpdateAction as BaseUserUpdateAction

from meldingen.actions.base import BaseListAction
from meldingen.models import User


class UserCreateAction(BaseUserCreateAction[User]): ...


class UserListAction(BaseUserListAction[User], BaseListAction[User]): ...


class UserRetrieveAction(BaseUserRetrieveAction[User]): ...


class UserUpdateAction(BaseUserUpdateAction[User]): ...


class UserDeleteAction(BaseUserDeleteAction[User]): ...
