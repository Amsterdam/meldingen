import pytest
from fastapi import HTTPException

from meldingen.api.utils import pagination_params, sort_param


@pytest.mark.parametrize(
    "limit, offset, match_limit, match_offset",
    [
        (None, None, 50, None),  # 50 is the default limit and None is the default offset
        (None, 5, 50, 5),  # 50 is the default limit and 5 is the expected offset
        (10, 5, 10, 5),  # 10 is the expected limit and 5 is the expected offset
    ],
)
def test_pagination_params(limit: int, offset: int, match_limit: int, match_offset: int) -> None:
    if limit is None:
        result = pagination_params(offset=offset)
    else:
        result = pagination_params(limit=limit, offset=offset)

    assert result["limit"] == match_limit
    assert result["offset"] == match_offset


@pytest.mark.parametrize(
    "attribute, direction",
    [("id", "ASC"), ("id", "DESC")],
)
def test_sort_param(attribute: str, direction: str) -> None:
    params = sort_param(f'["{attribute}","{direction}"]')

    assert params.get_attribute_name() == attribute
    assert params.get_direction() == direction


def test_sort_param_invalid_input() -> None:
    with pytest.raises(HTTPException):
        sort_param("asdf")
