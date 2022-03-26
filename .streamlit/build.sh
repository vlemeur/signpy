DOCKER_TAG=$(cat .streamlit/VERSION.txt)
DOCKER_REPO="signpy"
LIBRARY_NAME="signpy"

# Building the local package wheels beforehand
python3 -m tox -e build

docker build \
    -f ./.streamlit/Dockerfile \
    -t ${DOCKER_REPO}:${DOCKER_TAG} \
    --build-arg LIBRARY_TAG=${DOCKER_TAG} \
    --build-arg LIBRARY_NAME=${LIBRARY_NAME} \
    .

echo "Open the app at 'localhost:8501'" and not the URLs suggested by the Streamlit prompt.

docker run -e DOCKER="DOCKER" -p 8501:8501 ${DOCKER_REPO}:${DOCKER_TAG}

