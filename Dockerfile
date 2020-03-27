FROM python:3-alpine
RUN apk update && apk add git openssh-client

COPY . /app
WORKDIR /app

RUN pip install -e .

COPY scripts/docker/gitconfig /root/.gitconfig

WORKDIR /git

ENTRYPOINT [ "tartufo" ]
CMD [ "-h" ]
