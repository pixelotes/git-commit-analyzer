#!/bin/sh
set -e

# Function to install jq based on available package manager
install_jq() {
    echo "jq not found. Installing..."
    
    # Check for package managers and install accordingly
    if command -v apt-get &> /dev/null; then
        echo "Using apt-get (Debian/Ubuntu)"
        apt-get update && apt-get install -y jq
    elif command -v yum &> /dev/null; then
        echo "Using yum (RHEL/CentOS)"
        yum install -y jq
    elif command -v dnf &> /dev/null; then
        echo "Using dnf (Fedora)"
        dnf install -y jq
    elif command -v zypper &> /dev/null; then
        echo "Using zypper (openSUSE)"
        zypper install -y jq
    elif command -v apk &> /dev/null; then
        echo "Using apk (Alpine)"
        apk add jq
    elif command -v pacman &> /dev/null; then
        echo "Using pacman (Arch)"
        pacman -S --noconfirm jq
    elif command -v brew &> /dev/null; then
        echo "Using brew (macOS/Linux)"
        brew install jq
    else
        echo "Error: No supported package manager found."
        echo "Please install jq manually from: https://stedolan.github.io/jq/"
        exit 1
    fi
}

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    install_jq
    
    # Verify installation
    if command -v jq &> /dev/null; then
        echo "jq successfully installed: $(jq --version)"
    else
        echo "Error: jq installation failed"
        exit 1
    fi
else
    echo "jq is already installed: $(jq --version)"
fi

# Debug output
echo "Current directory: $(pwd)"
echo "GITHUB_ACTION_PATH: $GITHUB_ACTION_PATH"
echo "GITHUB_WORKSPACE: $GITHUB_WORKSPACE"
echo "Repository contents:"
ls -la
echo "Last 10 commits:"
git -C $GITHUB_WORKSPACE log --oneline -n 10


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
    if ! [ -n "$START_DATE" ]; then
        # Use PR created_at as start date (strip time)
        START_DATE=$(echo "$PR_CREATED_AT" | cut -d'T' -f1)
    fi

    if ! [ -n "$END_DATE" ]; then
        # Use today as end date
        END_DATE=$(date -u +%Y-%m-%d)
    fi
  fi
fi

# Start date: 00:00:00 (beginning of day)
START_DATETIME="${START_DATE}T00:00:00"
# End date: 23:59:59 (end of day)
END_DATETIME="${END_DATE}T23:59:59"

# Debug print (optional)
echo "Using start date: $START_DATETIME"
echo "Using end date: $END_DATETIME"
echo "Repository path: $GITHUB_WORKSPACE"
echo "Using model: $INPUT_MODEL"
echo "Output file: $GITHUB_WORKSPACE/security-report.json"

# Run analysis with dates resolved
python "/app/git_commit_analyzer.py" \
  --repo $GITHUB_WORKSPACE/ \
  --start-date "$START_DATETIME" \
  --end-date "$END_DATETIME" \
  --model "$INPUT_MODEL" \
  --output "$GITHUB_WORKSPACE/security-report.json"

# Post results as check
echo "Analysis completed. Review security-report.json for details."
