FROM python:3.10-slim
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir requests

# Install ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama in background and run analyzer
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
