FROM python:3-alpine
RUN apk update && apk add git

COPY . /app
WORKDIR /app

RUN pip install -e .

WORKDIR /git

ENTRYPOINT [ "tartufo"]
CMD ["-h"]
