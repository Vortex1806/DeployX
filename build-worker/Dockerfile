FROM ubuntu:24.04

RUN apt-get update && \
    apt-get install -y curl ca-certificates git python3 python3-pip python3-venv && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /home/app

# Isolated venv so pip doesn't fight Ubuntu 24.04's externally-managed-environment guard
RUN python3 -m venv /home/app/.venv
ENV PATH="/home/app/.venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY build.py .

ENTRYPOINT ["python3", "build.py"]
