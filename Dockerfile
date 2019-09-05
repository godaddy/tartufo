FROM python:3-alpine
RUN apk add --no-cache git && pip install tartufo
RUN adduser -S tartufo
USER tartufo
WORKDIR /proj
ENTRYPOINT [ "tartufo" ]
CMD [ "-h" ]
