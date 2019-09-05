#!/usr/bin/env bash
if [[ "${TRAVIS_PULL_REQUEST}" == "false" ]] && [[ "${TRAVIS_BRANCH}" == "master" ]]; then
    echo "${DOCKER_PASSWORD}" | docker login -u "${DOCKER_USERNAME}" --password-stdin
    docker build -t tartufo .
    docker images
    docker tag tartufo "${DOCKER_USERNAME}"/tartufo
    docker push "${DOCKER_USERNAME}"/tartufo:latest
else
    echo "Skipping publish as we are on a Pull Request"
fi
