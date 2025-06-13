#!/bin/sh
set -e

# Start Ollama in background
ollama serve &
sleep 5  # Wait for Ollama to initialize

# Pull the model
ollama pull "$INPUT_MODEL"

# Run analysis
python git_commit_analyzer.py \
  --repo /github/workspace \
  --start-date "$INPUT_START_DATE" \
  --end-date "$INPUT_END_DATE" \
  --model "$INPUT_MODEL" \
  --output "$GITHUB_WORKSPACE/security-report.json"

# Post results as check
echo "Analysis completed. Review security-report.json for details."
