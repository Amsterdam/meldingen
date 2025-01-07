# Dependency Management

Poetry is utilized as the dependency management tool for the Meldingen 
application. This guide explains how to add and update dependencies using 
Poetry within the Docker environment.

For more detailed information about Poetry take a look at the [official Poetry documentation](https://python-poetry.org/).

## Adding Dependencies

To add a new dependency, execute the following command:

```bash
docker compose run --rm --user=root meldingen poetry add {dependency}
```

For example, to add the pydantic dependency:

```bash
docker-compose run --rm --user=root meldingen poetry add pydantic
```

This command installs the specified dependency into the project.

### Rootless Docker
Because the container is running rootless and Poetry needs to make changes
to the filesystem, we need to execute our commands as the root user.

## Development, Linting, and Testing Dependencies

When adding dependencies specifically for development, linting, or testing 
purposes, an additional parameter `-G dev` should be included. For instance, 
to add a development dependency such as pytest, use the following command:

```bash
docker-compose run --rm --user=root meldingen poetry add -G dev pytest
```

Including `-G dev` ensures that the dependency is added as a development 
dependency.

## Updating Dependencies

To update existing dependencies to their latest compatible versions, use the 
following command:

```bash
docker-compose run --rm --user=root meldingen poetry update
```

This command updates all dependencies to their latest compatible versions based 
on the constraints defined in the `pyproject.toml` file.

By following these instructions, you can manage dependencies effectively using 
Poetry within the Docker environment of the Meldingen application.
