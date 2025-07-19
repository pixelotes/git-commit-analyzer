# Git Commit Security Analyzer

A Python tool that analyzes git commits for suspicious or malicious code changes using AI-powered analysis through [Ollama](https://github.com/ollama/ollama). This tool **flags potentially dangerous commits for manual review** and helps security teams and developers identify commits that warrant closer inspection.

**⚠️ Important**: This tool is designed to assist in identifying commits that may require manual security review. It is **not a substitute for professional security audits** or comprehensive code review processes.

---

## 📚 Table of Contents

- [🚀 Features](#-features)
- [📋 Prerequisites](#-prerequisites)
  - [1. Install Ollama](#1-install-ollama)
  - [2. Start Ollama Service](#2-start-ollama-service)
- [🐳 Docker Usage (Recommended)](#-docker-usage-recommended)
  - [Build the Docker Image](#build-the-docker-image)
  - [Run Analysis with Docker](#run-analysis-with-docker)
    - [Basic Usage (Interactive Model Selection)](#basic-usage-interactive-model-selection)
    - [With Specific Model](#with-specific-model)
    - [Custom Output Location](#custom-output-location)
  - [Docker Network Alternatives](#docker-network-alternatives)
- [🖥️ Local Python Usage](#️-local-python-usage)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Usage](#usage)
- [📊 Command Line Options](#-command-line-options)
- [📈 Understanding the Output](#-understanding-the-output)
  - [Sample Output](#sample-output)
  - [JSON Report Structure](#json-report-structure)
- [🔧 How It Works](#-how-it-works)
- [🛠️ Troubleshooting](#️-troubleshooting)
  - [Common Issues](#common-issues)
  - [Performance Tips](#performance-tips)
- [📝 To-Do](#-to-do)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)
- [🙏 Acknowledgments](#-acknowledgments)
- [⚠️ Disclaimer](#️-disclaimer)

---

## 🚀 Features

- **AI-Powered Analysis**: Uses local Ollama models to analyze code changes
- **Interactive Model Selection**: Automatically discovers and lets you choose from available Ollama models
- **Performance Tracking**: Tracks analysis time for each commit and provides timing statistics
- **Flexible Date Ranges**: Analyze commits within specific time periods
- **Detailed Reporting**: Generates comprehensive JSON reports with verdicts and reasoning
- **Docker Support**: Run containerized for consistent environments
- **Batch Processing**: Analyzes multiple commits efficiently with progress tracking

## 📋 Prerequisites

### 1. Install Ollama

Ollama is required to run the AI models locally. Follow the installation instructions for your platform:

**Official Ollama Repository**: https://github.com/ollama/ollama

#### Quick Installation:

**Linux & macOS:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
Download and run the installer from https://ollama.ai/download

#### Install a Model:
After installing Ollama, pull one of the recommended models for code analysis:

**Recommended Models (in order of preference):**

```bash
# Best for code analysis - specialized coding model
ollama pull qwen2.5-coder:7b

# Faster alternative - good balance of speed and accuracy
ollama pull qwen2.5-coder:3b

# Compact but capable model
ollama pull phi4-mini

# General purpose alternative
ollama pull llama3
```

**Model Recommendations:**
- **qwen2.5-coder:7b**: Best accuracy for code analysis (~4GB RAM required)
- **qwen2.5-coder:3b**: Good balance of speed and accuracy (~2GB RAM required)  
- **phi4-mini**: Compact and efficient (~1.5GB RAM required)
- **llama3**: General purpose model, decent for code analysis

⚠️ **Important**: Models under 3B parameters typically produce unreliable results for security analysis. Models with 3-4B parameters can be workable on low-end systems, but we recommend using models 7B or larger for production use. More capable models will produce better analysis with less false positives.

See the [Ollama model library](https://ollama.ai/library) for the complete list of available models.

### 2. Start Ollama Service

Make sure Ollama is running:
```bash
ollama serve
```

The service will be available at `http://localhost:11434` by default.

## 🐳 Docker Usage (Recommended)

### Build the Docker Image

```bash
git clone <your-repo-url>
cd git-commit-security-analyzer
docker build -t git-commit-analyzer .
```

### Run Analysis with Docker

#### Basic Usage (Interactive Model Selection):
```bash
docker run --rm -it \
  --network host \
  -v /path/to/your/repo:/repo \
  -v $(pwd):/output \
  git-commit-analyzer \
  --repo /repo \
  --start-date "2024-01-01" \
  --end-date "2024-01-31"
```

#### With Specific Model:
```bash
docker run --rm -it \
  --network host \
  -v /path/to/your/repo:/repo \
  -v $(pwd):/output \
  git-commit-analyzer \
  --repo /repo \
  --start-date "2024-01-01" \
  --end-date "2024-01-31" \
  --model "qwen2.5-coder:7b"
```

#### Custom Output Location:
```bash
docker run --rm -it \
  --network host \
  -v /path/to/your/repo:/repo \
  -v /path/to/output:/output \
  git-commit-analyzer \
  --repo /repo \
  --start-date "2024-01-01" \
  --end-date "2024-01-31" \
  --output /output/security-analysis.json
```

### Docker Network Alternatives

If you prefer not to use `--network host`, you can specify Ollama's location:

```bash
# Using host.docker.internal (Docker Desktop)
docker run --rm -it \
  -v /path/to/repo:/repo \
  -v $(pwd):/output \
  git-commit-analyzer \
  --repo /repo \
  --start-date "2024-01-01" \
  --end-date "2024-01-31" \
  --api-url "http://host.docker.internal:11434/api/generate"

# Using specific IP address
docker run --rm -it \
  -v /path/to/repo:/repo \
  -v $(pwd):/output \
  git-commit-analyzer \
  --repo /repo \
  --start-date "2024-01-01" \
  --end-date "2024-01-31" \
  --api-url "http://192.168.1.100:11434/api/generate"
```

## 🖥️ Local Python Usage

### Requirements

- Python 3.7+
- Git
- Ollama running locally

### Installation

```bash
git clone <your-repo-url>
cd git-commit-security-analyzer
pip install requests
```

### Usage

```bash
# Interactive model selection
python git_commit_analyzer.py \
  --repo /path/to/repository \
  --start-date "2024-01-01" \
  --end-date "2024-01-31"

# With specific model
python git_commit_analyzer.py \
  --repo /path/to/repository \
  --start-date "2024-01-01" \
  --end-date "2024-01-31" \
  --model "qwen2.5-coder:7b"

# With custom Ollama URL and timeout
python git_commit_analyzer.py \
  --repo /path/to/repository \
  --start-date "2024-01-01" \
  --end-date "2024-01-31" \
  --api-url "http://localhost:11434/api/generate" \
  --timeout 180

# With Slack output
python git_commit_analyzer.py \
  --repo /path/to/repository \
  --start-date "2024-01-01" \
  --model qwen3:8b
  --slack-webhook "https://<webhook>"
```

## 📊 Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--repo` | Path to the git repository (required) | - |
| `--start-date` | Start date in YYYY-MM-DD format (required) | - |
| `--end-date` | End date in YYYY-MM-DD format (required) | Current date |
| `--model` | Ollama model to use (if not specified, shows interactive selection) | - |
| `--api-url` | Ollama API URL | `http://localhost:11434/api/generate` |
| `--output` | Output JSON file path | `{repo-name}-report.json` |
| `--timeout` | API request timeout in seconds | `120` |
| `--debug` | Saves LLM responses to .json files | `false` |
| `--prompt` | Path to external prompt | Internal prompt |
| `--create-sample-prompt` | Saves a sample prompt to "custom_prompt.txt" | - |
| `--slack-webhook` | Posts a summary to Slack after finishing the analysis | - |

## 📈 Understanding the Output

The tool analyzes each commit and provides:

- **PASS**: The commit appears safe and doesn't contain suspicious code
- **FAIL**: The commit contains potentially suspicious or malicious changes
- **ERROR**: Analysis failed due to technical issues

### Sample Output

```
Processing commit 1/5: abc123def456
  Author: John Doe <john@example.com>
  Date: 2024-01-15 10:30:00
  Message: Add user authentication feature
  Sending to Ollama for analysis... received response.
  VERDICT: PASS
  REASONING: This commit adds standard authentication functionality with proper input validation and secure password handling.
  ANALYSIS TIME: 2.3s
  Progress: 1/5 commits analyzed (20.0%)
```

### JSON Report Structure

```json
[
  {
    "hash": "abc123def456",
    "author": "John Doe <john@example.com>",
    "date": "2024-01-15 10:30:00",
    "message": "Add user authentication feature",
    "verdict": "PASS",
    "reasoning": "This commit adds standard authentication functionality...",
    "analysis_time_seconds": 2.34
  }
]
```

## 🔧 How It Works

1. **Commit Discovery**: The tool uses `git log` to find commits within the specified date range
2. **Diff Extraction**: For each commit, it extracts the full diff showing code changes
3. **AI Analysis**: The diff is sent to a local Ollama model with a specialized security analysis prompt
4. **Verdict Generation**: The AI model responds with either "PASS" or "FAIL" along with reasoning
5. **Report Generation**: Results are compiled into a detailed JSON report with timing information

The AI model is prompted to look for:
- Suspicious code patterns
- Potential security vulnerabilities
- Malicious code injection
- Unusual or obfuscated code changes
- Backdoors or unauthorized access mechanisms

## 🛠️ Troubleshooting

### Common Issues

**"Error querying available models"**
- Ensure Ollama is running: `ollama serve`
- Check if the Ollama API is accessible: `curl http://localhost:11434/api/tags`

**"HTTP Error: 404"**
- The specified model might not be installed: `ollama pull qwen2.5-coder:7b`
- Check available models: `ollama list`

**"Timeout while waiting for Ollama response"**
- Increase timeout with `--timeout 300`
- Consider using a smaller, faster model
- Check if your system has sufficient resources

**Docker network issues**
- Use `--network host` for simplest setup
- Or specify the correct Ollama URL with `--api-url`

### Performance Tips

- **Model Selection**: 
  - **qwen2.5-coder:7b**: Best accuracy but requires ~4GB RAM
  - **qwen2.5-coder:3b**: Good balance of speed and accuracy (~2GB RAM)
  - **phi4-mini**: Fastest option while maintaining decent quality (~1.5GB RAM)
  - Avoid models under 3B parameters for production use
- **Batch Size**: The tool processes commits sequentially to avoid overwhelming the AI model
- **Resource Allocation**: Ensure adequate RAM and CPU for your chosen model
- **Timeout Settings**: Adjust based on your model size and hardware capabilities

## 📝 To-Do

- [X] Allow using custom prompts
- [X] If ollama lists a single model, use it by default
- [X] Add an option to send the summary report to Slack
- [X] Make the end date optional, make current date default value
- [ ] Add better error handling logic
- [ ] Let users choose to analyze the commits in ascending or descending order
- [ ] Make report output more customizable
- [ ] Consider supporting more backends

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Ollama](https://github.com/ollama/ollama) for providing an excellent local AI model runtime
- The open-source community for various AI models used in security analysis

## ⚠️ Disclaimer

This tool is designed to assist in security analysis but should not be the sole method for detecting malicious code. Always combine automated analysis with manual code review and other security practices. The accuracy of results depends on the AI model used and the complexity of the code changes being analyzed.

**IMPORTANT LEGAL DISCLAIMER**: This software is provided "as is" without warranty of any kind, express or implied. The author(s) disclaim all warranties, including but not limited to warranties of merchantability, fitness for a particular purpose, and non-infringement. In no event shall the author(s) be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the software or the use or other dealings in the software. 

Users assume full responsibility for the use of this tool and any consequences resulting from its use. This tool is not intended to replace professional security audits or expert manual code review. Any security decisions made based on the output of this tool are the sole responsibility of the user.
