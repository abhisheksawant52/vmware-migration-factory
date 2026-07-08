# Slim single-stage image packaging the vmf CLI.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir .

# Run as a non-root user.
RUN useradd --create-home --uid 10001 vmf
USER vmf

ENTRYPOINT ["vmf"]
CMD ["--help"]
