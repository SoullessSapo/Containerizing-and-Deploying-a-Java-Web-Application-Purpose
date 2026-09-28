#!/usr/bin/env bash
# Publishes the image to Docker Hub with the tags 1.0 and latest.
#
# Usage: DOCKERHUB_USER=<dockerhub-user> scripts/publish-dockerhub.sh
#        DOCKERHUB_USER=<dockerhub-user> MULTIARCH=1 scripts/publish-dockerhub.sh
#
# MULTIARCH=1 builds for linux/amd64 and linux/arm64 with buildx. Use it when
# building on an Apple Silicon Mac: an arm64-only image fails on a t3 (x86_64)
# instance with "exec format error".
set -euo pipefail
cd "$(dirname "$0")/.."

: "${DOCKERHUB_USER:?Set DOCKERHUB_USER to your Docker Hub username}"
REPOSITORY="$DOCKERHUB_USER/virtualization-lab"
VERSION="${VERSION:-1.0}"

docker login
mvn -q clean package

if [ "${MULTIARCH:-0}" = "1" ]; then
  docker buildx build --platform linux/amd64,linux/arm64 \
    -t "$REPOSITORY:$VERSION" -t "$REPOSITORY:latest" --push .
  docker buildx imagetools inspect "$REPOSITORY:$VERSION"
else
  docker build -t "$REPOSITORY:$VERSION" .
  docker tag "$REPOSITORY:$VERSION" "$REPOSITORY:latest"
  docker push "$REPOSITORY:$VERSION"
  docker push "$REPOSITORY:latest"
fi

echo "Published https://hub.docker.com/r/$REPOSITORY"
