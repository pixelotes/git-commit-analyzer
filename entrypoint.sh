#!/bin/sh
set -e

# Start Ollama in background
ollama serve &
sleep 5  # Wait for Ollama to initialize

# Pull the model
ollama pull "$INPUT_MODEL"

# Default values from inputs
START_DATE="${INPUT_START_DATE%%T*}"
END_DATE="${INPUT_END_DATE%%T*}"

# Check if running in a pull_request event
if [ -n "$GITHUB_EVENT_PATH" ] && grep -q '"pull_request"' "$GITHUB_EVENT_PATH"; then
  # Extract PR creation date (e.g. "2024-07-15T12:34:56Z") from event JSON
  PR_CREATED_AT=$(jq -r '.pull_request.created_at' "$GITHUB_EVENT_PATH")
  
  if [ "$PR_CREATED_AT" != "null" ]; then
    # Use PR created_at as start date (strip time)
    START_DATE=$(echo "$PR_CREATED_AT" | cut -d'T' -f1)
    # Use today as end date
    END_DATE=$(date -u +%Y-%m-%d)
  fi
fi

# Debug print (optional)
echo "Using start date: $START_DATE"
echo "Using end date: $END_DATE"

# Run analysis with dates resolved
python git_commit_analyzer.py \
  --repo /github/workspace \
  --start-date "$START_DATE" \
  --end-date "$END_DATE" \
  --model "$INPUT_MODEL" \
  --output "$GITHUB_WORKSPACE/security-report.json"

# Post results as check
echo "Analysis completed. Review security-report.json for details."
