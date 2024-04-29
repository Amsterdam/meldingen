from typing import Any

import pytest

from meldingen.api.utils import pagination_params


@pytest.mark.asyncio
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
