FROM ghcr.io/astral-sh/uv:0.11.7 AS uv
FROM python:3.14-slim

COPY --from=uv /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY signpy ./signpy
COPY .streamlit/config.toml ./.streamlit/config.toml
RUN uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"
ENTRYPOINT ["streamlit", "run", "signpy/signstream.py"]
CMD ["--server.address=0.0.0.0", "--server.headless=true"]
