FROM python:3.11-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/fontguard
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY src ./src
COPY data ./data
RUN pip install --no-cache-dir .
WORKDIR /workspace
ENTRYPOINT ["fontguard"]
CMD ["scan", ".", "--no-cache"]

FROM runtime AS test
WORKDIR /opt/fontguard
RUN pip install --no-cache-dir ".[dev]" python-docx python-pptx
COPY tests ./tests
COPY scripts ./scripts
COPY examples ./examples
ENTRYPOINT ["python", "-m", "pytest"]
CMD ["-q"]

FROM runtime AS final
