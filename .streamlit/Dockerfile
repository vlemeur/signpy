FROM python:3.9.10-slim

ARG LIBRARY_TAG
ARG LIBRARY_NAME

ENV LIBRARY_TAG=$LIBRARY_TAG
ENV LIBRARY_NAME=$LIBRARY_NAME

WORKDIR /app

# Install
COPY ./.streamlit/streamlit-requirements.txt ./streamlit-requirements.txt
RUN pip3 install -r streamlit-requirements.txt

# Get streamlit scripts
# Necessary to create a nested dictionnary so the pickle paths work here as they do locally
COPY ./${LIBRARY_NAME}/signstream.py ./signstream/signstream.py

# Copying the logo directly into the docker image
COPY ./static ./static

# Copy streamlit config (done only now to optimize cache)
COPY ./.streamlit/config.toml ./.streamlit/config.toml

# Get Models
COPY ./pickles ./pickles

EXPOSE 8501

ENTRYPOINT ["streamlit", "run"]

CMD ["signstream/signstream.py"]