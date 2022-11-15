FROM python:3.10-slim as base

WORKDIR /app

FROM base as builder

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.1.12

RUN apt-get update && apt-get upgrade -y && apt-get install make cmake gcc libssl-dev wget -y
RUN wget https://github.com/libgit2/libgit2/archive/refs/tags/v1.4.0.tar.gz -O libgit2-1.4.0.tar.gz \
    && tar xzf libgit2-1.4.0.tar.gz \
    && cd libgit2-1.4.0/ \
    && cmake . \
    && make \
    && make install
RUN apt-get install libffi-dev -y
RUN pip --no-cache-dir install "poetry==$POETRY_VERSION"
RUN python -m venv /venv

COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt | /venv/bin/pip install -r /dev/stdin

COPY . .
RUN poetry build && /venv/bin/pip install dist/*.whl

FROM base as final

RUN apt-get update && apt-get upgrade -y && apt-get install -y git openssh-client
COPY --from=builder /venv /venv
COPY scripts/docker/gitconfig /root/.gitconfig

WORKDIR /git

ENTRYPOINT [ "/venv/bin/tartufo" ]
CMD [ "-h" ]
