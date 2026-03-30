FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-dejavu-core \
    ca-certificates \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.docker.txt .
RUN pip install --no-cache-dir -r requirements.docker.txt

COPY . .

RUN mkdir -p /app/runs

CMD ["python", "src/agent_sandbox.py", "--backend", "stub", "--mode", "dom"]