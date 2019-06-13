#!/usr/bin/env bash
if [[ $TRAVIS_PULL_REQUEST == "false" ]] && [[ $TRAVIS_BRANCH == "docker_build_and_publish" ]]; then
    docker login -u "$DOCKER_USERNAME" -p "$DOCKER_PASSWORD"
    docker build -t trufflehog .
    docker images
    docker tag trufflehog $DOCKER_USERNAME/trufflehog
    docker push $DOCKER_USERNAME/trufflehog:latest
else
    echo "Skipping publish as we are on a Pull Request"
fi
