FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY src/requirements.txt /app/src/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /app/src/requirements.txt

COPY shared /app/shared
COPY src /app/src

WORKDIR /app/src

CMD ["python", "main.py"]
