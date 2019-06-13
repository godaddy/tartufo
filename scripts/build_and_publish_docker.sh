#!/usr/bin/env bash
if [[ $TRAVIS_PULL_REQUEST == "false" ]] && [[ $TRAVIS_BRANCH == "docker_build_and_publish" ]]; then
    docker login -u "$DOCKER_USERNAME" -p "$DOCKER_PASSWORD"
    docker build -t travis-ci-build-stages-demo .
    docker images
    docker tag travis-ci-build-stages-demo $DOCKER_USERNAME/travis-ci-build-stages-demo
else
    echo "Skipping publish as we are on a Pull Request"
fi
