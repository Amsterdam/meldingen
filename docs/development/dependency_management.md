# Dependency Management

uv is utilized as the dependency management tool for the Meldingen
application. This guide explains how to add and update dependencies using
uv within the Docker environment.

For more detailed information about uv, see the [official uv documentation](https://docs.astral.sh/uv/).

## Adding Dependencies

To add a new dependency, execute the following command:

```bash
docker compose run --rm --user=root meldingen uv add {dependency}
```

For example, to add the pydantic dependency:

```bash
docker compose run --rm --user=root meldingen uv add pydantic
```

This command installs the specified dependency into the project.

### Rootless Docker
Because the container is running rootless and uv needs to make changes
to the filesystem, we need to execute our commands as the root user.

## Development, Linting, and Testing Dependencies

When adding dependencies specifically for development, linting, or testing
purposes, the `--group dev` parameter should be included. For instance,
to add a development dependency such as pytest, use the following command:

```bash
docker compose run --rm --user=root meldingen uv add --group dev pytest
```

Including `--group dev` ensures that the dependency is added as a development
dependency.

## Updating Dependencies

To update existing dependencies to their latest compatible versions, use the
following command:

```bash
docker compose run --rm --user=root meldingen uv lock --upgrade
```

This command updates the lockfile (`uv.lock`) to the latest compatible versions based
on the constraints defined in the `pyproject.toml` file.

By following these instructions, you can manage dependencies effectively using
uv within the Docker environment of the Meldingen application.

To check which dependencies are outdated, you can use the following command:

```bash
docker compose run --rm --user=root meldingen uv tree --outdated
```
