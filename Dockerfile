FROM python:3.12

WORKDIR /opt/meldingen

# Install Poetry
RUN set eux; \
    curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python; \
    cd /usr/local/bin; \
    ln -s /opt/poetry/bin/poetry; \
    poetry config virtualenvs.create false; \
    poetry self add poetry-sort

COPY ./pyproject.toml ./poetry.lock /opt/meldingen/

# Allow installing dev dependencies to run tests
ARG INSTALL_DEV=false
RUN set -eux; \
    if [ "$INSTALL_DEV" = "true" ]; then \
      poetry install --no-root --no-directory; \
    else \
      poetry install --no-root --no-directory --only main; \
    fi

COPY . /opt/meldingen
ENV PYTHONPATH=/opt/meldingen

ENTRYPOINT ["/opt/meldingen/meldingen-entrypoint.sh"]
CMD ["uvicorn", "meldingen.main:app", "--proxy-headers", "--host", "0.0.0.0", "--port", "80", "--reload"]
