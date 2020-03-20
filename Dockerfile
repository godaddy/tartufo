FROM python:3-alpine
RUN apk update && apk add git openssh-client

COPY . /app
WORKDIR /app

RUN pip install -e .

WORKDIR /git

COPY scripts/docker/entrypoint.sh /entrypoint.sh
COPY scripts/docker/ssh-askpass.sh /ssh-askpass.sh
COPY scripts/docker/gitconfig /root/.gitconfig

ENTRYPOINT [ "/entrypoint.sh" ]
CMD [ "-h" ]
