#!/bin/bash

IMAGE_NAMESPACE=godaddy
IMAGE_NAME=tartufo

# Move into the scripts folder
cd "$( dirname "${BASH_SOURCE[0]}" )"
IMAGE_VERSION=$(awk -F'[ ="]+' '$1 == "version" { print $2 }' ../pyproject.toml)
IMAGE_FULL_NAME=${IMAGE_NAMESPACE}/${IMAGE_NAME}

# Go back to the top level of the project
cd ..
# Log in to Docker Hub
echo "${DOCKER_PASSWORD}" | docker login -u "${DOCKER_USERNAME}" --password-stdin
# Build and tag as the "latest" version of the image
docker build -t ${IMAGE_FULL_NAME}:latest .
# Give the build a more specific version tag, from the VERSION file
docker tag ${IMAGE_FULL_NAME}:latest ${IMAGE_FULL_NAME}:${IMAGE_VERSION}
docker push ${IMAGE_FULL_NAME}:latest
docker push ${IMAGE_FULL_NAME}:${IMAGE_VERSION}
