#!/bin/sh
set -eu

DOCKER_TAG=$(cat .streamlit/VERSION.txt)
DOCKER_REPO="signpy"

docker build -f .streamlit/Dockerfile -t "${DOCKER_REPO}:${DOCKER_TAG}" .
printf '%s\n' "Open the app at http://localhost:8501"
docker run --rm -p 8501:8501 "${DOCKER_REPO}:${DOCKER_TAG}"
