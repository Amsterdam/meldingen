import tomllib


def get_version() -> str:
    """Reads the version from pyproject.toml"""
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
        version = data["tool"]["poetry"]["version"]
        return f"{version}"
