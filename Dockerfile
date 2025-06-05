# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set metadata
LABEL description="Git Commit Security Analyzer with Ollama integration"
LABEL version="1.0"

# Install git and other necessary system packages
RUN apt-get update && \
    apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir requests

# Install ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Copy the analyzer script
COPY git_commit_analyzer.py /app/git_commit_analyzer.py

# Create a directory for mounting repositories
RUN mkdir -p /repo

# Create a directory for output reports
RUN mkdir -p /output

# Set the entrypoint to the script
ENTRYPOINT ["python3", "/app/git_commit_analyzer.py"]

# Default command shows help
CMD ["--help"]
