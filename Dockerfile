FROM python:3.11-slim as base

WORKDIR /app

FROM base as builder

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.2.2

RUN pip --no-cache-dir install "poetry==$POETRY_VERSION"
RUN python -m venv /venv

COPY pyproject.toml poetry.lock ./
RUN . /venv/bin/activate && poetry install --no-root --only=main

COPY . .
RUN poetry build -f wheel && /venv/bin/pip install dist/*.whl

FROM base as final

RUN apt-get update && apt-get upgrade -y && apt-get install -y git openssh-client
COPY --from=builder /venv /venv
COPY scripts/docker/gitconfig /root/.gitconfig

WORKDIR /git

ENTRYPOINT [ "/venv/bin/tartufo" ]
CMD [ "-h" ]
