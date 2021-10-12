#!/bin/bash

IMAGE_NAMESPACE=godaddy
IMAGE_NAME=tartufo

# Move into the scripts folder
cd "$( dirname "${BASH_SOURCE[0]}" )"
IMAGE_VERSION=$(awk -F'[ ="]+' '$1 == "version" { print $2 }' ../pyproject.toml)
VERSION_SUFFIX=$(echo ${IMAGE_VERSION} |  awk -F '-' '{print $2}')
IMAGE_FULL_NAME=${IMAGE_NAMESPACE}/${IMAGE_NAME}

# Go back to the top level of the project
cd ..
# Log in to Docker Hub
echo "${DOCKER_PASSWORD}" | docker login -u "${DOCKER_USERNAME}" --password-stdin
# Build, tag & publish image with the specific version tag
docker build -t ${IMAGE_FULL_NAME}:${IMAGE_VERSION} .
docker push ${IMAGE_FULL_NAME}:${IMAGE_VERSION}
# If this is a stable release(no version suffix), update latest docker image
if [  "${VERSION_SUFFIX}" == "" ]; then
    docker tag ${IMAGE_FULL_NAME}:${IMAGE_VERSION} ${IMAGE_FULL_NAME}:latest
    docker push ${IMAGE_FULL_NAME}:latest
fi
