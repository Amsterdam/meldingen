FROM python:3.13-slim-bookworm

WORKDIR /opt/meldingen

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      git \
      libmagic1 \
      media-types \
    && rm -rf /var/lib/apt/lists/*

# Add user
RUN groupadd --gid 1000 meldingen && useradd --uid 1000 --gid 1000 --system meldingen

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT="/usr/local"

COPY pyproject.toml uv.lock* ./

# Allow installing dev dependencies to run tests
ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ]; then \
      uv sync --frozen --no-install-project; \
    else \
      uv sync --frozen --no-install-project --no-dev; \
    fi

COPY . /opt/meldingen

# Provide a default classification seed file from the version-controlled examples when the
# deploy pipeline hasn't supplied one (seed/classifications.json is gitignored). The -n flag
# ensures an injected seed file is never overwritten.
RUN cp -n seed/examples/classifications.json seed/classifications.json

ENV PYTHONPATH=/opt/meldingen

USER meldingen

ENTRYPOINT ["/opt/meldingen/meldingen-entrypoint.sh"]
CMD ["fastapi", "run", "/opt/meldingen/meldingen/main.py"]
