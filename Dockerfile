FROM ollama/ollama:latest AS ollama
RUN ollama pull qwen2.5-coder:3b

FROM python:3.10-slim
WORKDIR /app

# Copy Ollama with preloaded model
COPY --from=ollama /usr/bin/ollama /usr/bin/ollama
COPY --from=ollama /var/lib/ollama /var/lib/ollama

# Install dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# Start Ollama in background and run analyzer
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
