from typing import Any

from meldingen.config import settings
from meldingen.main import add_custom_open_api_scheme, get_application


def _authorization_code_flow(schema: dict[str, Any]) -> dict[str, Any]:
    scheme = schema["components"]["securitySchemes"]["OAuth2AuthorizationCodeBearer"]
    flow: dict[str, Any] = scheme["flows"]["authorizationCode"]
    return flow


class TestCustomOpenApiScheme:
    def test_declares_the_configured_scopes(self) -> None:
        app = get_application()
        add_custom_open_api_scheme(app)

        flow = _authorization_code_flow(app.openapi())

        assert flow["scopes"] == {scope: "" for scope in settings.auth_scopes}
        assert flow["authorizationUrl"] == settings.auth_url
        assert flow["tokenUrl"] == settings.token_url

    def test_declares_top_level_security(self) -> None:
        app = get_application()
        add_custom_open_api_scheme(app)

        assert app.openapi()["security"] == [{"OAuth2AuthorizationCodeBearer": []}]

    def test_survives_schema_regeneration(self) -> None:
        """FastAPI 0.138 invalidates a pre-built `openapi_schema` on a routes-version
        check, which silently dropped the scopes Scalar binds `selectedScopes` to."""
        app = get_application()
        add_custom_open_api_scheme(app)

        first = app.openapi()
        second = app.openapi()

        assert _authorization_code_flow(first)["scopes"] == _authorization_code_flow(second)["scopes"]
        assert _authorization_code_flow(second)["scopes"] != {}
        assert "security" in second
