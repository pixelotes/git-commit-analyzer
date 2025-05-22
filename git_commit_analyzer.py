#!/usr/bin/env python3
"""
Git Commit Security Analyzer (Ollama Version)

This script analyzes git commits between two dates and uses Ollama to check for
suspicious or malicious code changes.

Usage:
    python git_commit_analyzer.py --repo /path/to/repo --start-date "YYYY-MM-DD" --end-date "YYYY-MM-DD" 
                                  [--api-url "http://localhost:11434/api/generate"] [--model "llama3"]
                                  [--timeout 120] [--debug]
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
import requests
from typing import List, Dict, Tuple, Optional


def parse_arguments():
    parser = argparse.ArgumentParser(description="Analyze git commits for suspicious code using Ollama")
    parser.add_argument("--repo", required=True, help="Path to the git repository")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--api-url", default="http://localhost:11434/api/generate",
                        help="Ollama API URL (default: http://localhost:11434/api/generate)")
    parser.add_argument("--model", help="Model to use (if not specified, will show available models)")
    parser.add_argument("--output", default="security_report.json", help="Output file for results")
    parser.add_argument("--debug", action="store_true", help="Enable detailed debug output")
    parser.add_argument("--timeout", type=int, default=120, help="API request timeout in seconds (default: 120)")
    return parser.parse_args()


def get_available_models(api_url: str) -> List[Dict]:
    """Query Ollama for available models"""
    try:
        # Convert generate URL to tags URL
        base_url = api_url.replace('/api/generate', '')
        tags_url = f"{base_url}/api/tags"
        
        print("Querying available models...", end="", flush=True)
        response = requests.get(tags_url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        models = data.get('models', [])
        print(f" found {len(models)} models.")
        return models
    except requests.exceptions.RequestException as e:
        print(f"\nError querying available models: {e}")
        print("Make sure Ollama is running and accessible.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error getting models: {e}")
        sys.exit(1)


def select_model_interactively(models: List[Dict]) -> str:
    """Present available models and let user choose"""
    if not models:
        print("No models available. Please install a model in Ollama first.")
        sys.exit(1)
    
    print("\nAvailable models:")
    for i, model in enumerate(models, 1):
        name = model['name']
        size = model.get('size', 0)
        modified = model.get('modified_at', 'Unknown')
        
        # Convert size to human readable format
        if size > 0:
            if size >= 1024**3:
                size_str = f"{size / (1024**3):.1f} GB"
            elif size >= 1024**2:
                size_str = f"{size / (1024**2):.1f} MB"
            else:
                size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = "Unknown size"
        
        print(f"  {i}. {name} ({size_str})")
    
    while True:
        try:
            choice = input(f"\nSelect a model (1-{len(models)}): ").strip()
            index = int(choice) - 1
            if 0 <= index < len(models):
                selected_model = models[index]['name']
                print(f"Selected model: {selected_model}")
                return selected_model
            else:
                print(f"Please enter a number between 1 and {len(models)}")
        except ValueError:
            print("Please enter a valid number")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)


def get_commits_between_dates(repo_path: str, start_date: str, end_date: str) -> List[str]:
    try:
        print("Fetching commits...", end="", flush=True)
        cmd = [
            "git", "-C", repo_path, "log",
            f"--since={start_date}", f"--until={end_date}",
            "--format=%H"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        commits = result.stdout.strip().split('\n')
        valid_commits = [c for c in commits if c]
        print(f" found {len(valid_commits)} commits.")
        return valid_commits
    except subprocess.CalledProcessError as e:
        print(f"\nError getting commits: {e}")
        print(f"STDERR: {e.stderr}")
        sys.exit(1)


def get_commit_details(repo_path: str, commit_hash: str) -> Dict:
    try:
        cmd_message = ["git", "-C", repo_path, "log", "-1", "--pretty=format:%s%n%b", commit_hash]
        message_result = subprocess.run(cmd_message, capture_output=True, text=True, check=True)
        commit_message = message_result.stdout.strip()

        cmd_info = ["git", "-C", repo_path, "log", "-1", "--pretty=format:%an <%ae>%n%ad", commit_hash]
        info_result = subprocess.run(cmd_info, capture_output=True, text=True, check=True)
        info_lines = info_result.stdout.strip().split('\n')
        author = info_lines[0]
        date = info_lines[1] if len(info_lines) > 1 else "Unknown"

        print("  Fetching diff...", end="", flush=True)
        cmd_diff = ["git", "-C", repo_path, "show", commit_hash]
        diff_result = subprocess.run(cmd_diff, capture_output=True, text=True, check=True)
        diff_content = diff_result.stdout.strip()
        print(" done.")

        return {
            "hash": commit_hash,
            "author": author,
            "date": date,
            "message": commit_message,
            "diff": diff_content
        }
    except subprocess.CalledProcessError as e:
        print(f"\n  Error getting commit details for {commit_hash}: {e}")
        print(f"  STDERR: {e.stderr}")
        return {
            "hash": commit_hash,
            "error": str(e),
            "stderr": e.stderr
        }


def analyze_commit_with_ollama(commit_data: Dict, api_url: str, model: str, timeout: int = 120, debug: bool = False) -> Tuple[str, Optional[str], Optional[Dict], float]:
    """Analyze commit with Ollama and return verdict, reasoning, raw_response, and analysis_time"""
    start_time = time.time()
    
    system_prompt = """You are a security expert analyzing git commits for suspicious or malicious code.
RESPONSE FORMAT REQUIREMENTS:
1. Your first line MUST contain EXACTLY ONE of these two words:
   - "OK"
   - "SUSPICIOUS"
2. Your second line MUST contain your reasoning for the verdict.
3. Do not use any emojis in your response.
4. Do not include any additional text before the verdict."""

    user_prompt = create_prompt(commit_data)
    
    full_prompt = f"{system_prompt}\n\n{user_prompt}"

    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False
    }

    payload_str = json.dumps(payload)
    print(f"  Sending to Ollama for analysis (payload size: {len(payload_str)} bytes)...", end="", flush=True)

    if len(payload_str) > 100_000:
        print("\n  Warning: payload size exceeds 100KB. This may cause timeouts or hangs.")

    raw_response = None
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=timeout)
        
        # Store raw response text for debugging
        raw_response_text = response.text
        
        # Check for HTTP errors and provide detailed output
        if response.status_code != 200:
            print(f"\n  ❌ HTTP Error: {response.status_code}")
            print(f"  Response content: {raw_response_text[:1000]}")
            analysis_time = time.time() - start_time
            return "ERROR", f"HTTP {response.status_code}: {raw_response_text[:500]}...", {"status_code": response.status_code, "content": raw_response_text}, analysis_time
        
        print(" received response.")
        
        # Try to parse JSON response
        try:
            result = response.json()
            raw_response = result  # Store the parsed JSON for debug output
        except json.JSONDecodeError as e:
            print(f"\n  ❌ JSON parse error: {e}")
            print(f"  Raw response: {raw_response_text[:1000]}")
            analysis_time = time.time() - start_time
            return "ERROR", f"Failed to parse JSON response: {str(e)}. Raw response: {raw_response_text[:500]}...", {"content": raw_response_text}, analysis_time

        # Debug output
        if debug:
            print("\n--- DEBUG: FULL API RESPONSE ---")
            print(json.dumps(result, indent=2))
            print("-------------------------------")

        # Check if response has the expected format
        if "response" not in result:
            print(f"\n  ❌ Missing 'response' field in API response")
            print(f"  Response structure: {list(result.keys())}")
            analysis_time = time.time() - start_time
            return "ERROR", f"Missing 'response' field in API response: {json.dumps(result)[:500]}...", result, analysis_time

        ai_response = result["response"].strip()
        
        lines = ai_response.split('\n', 1)
        verdict = lines[0].strip()
        reasoning = lines[1].strip() if len(lines) > 1 else "No reasoning provided"

        # Handle case where model outputs more text before the verdict
        if verdict not in ["OK", "SUSPICIOUS"]:
            # Try to find verdict in the text
            if "OK" in ai_response.upper().split() and "SUSPICIOUS" not in ai_response.upper():
                verdict = "OK"
                print(f"  Warning: AI returned improperly formatted verdict. Found 'OK' in response.")
            elif "SUSPICIOUS" in ai_response.upper():
                verdict = "SUSPICIOUS"
                print(f"  Warning: AI returned improperly formatted verdict. Found 'SUSPICIOUS' in response.")
            else:
                print(f"  Warning: AI returned invalid verdict. Treating as SUSPICIOUS.")
                verdict = "SUSPICIOUS"
                
            if not reasoning or reasoning == "No reasoning provided":
                reasoning = f"AI response: {ai_response}"

        analysis_time = time.time() - start_time
        return verdict, reasoning, raw_response, analysis_time

    except requests.exceptions.Timeout:
        print("\n  ❌ Error: API call timed out after 120 seconds.")
        analysis_time = time.time() - start_time
        return "ERROR", "Timeout while waiting for Ollama response (120s).", None, analysis_time
    except requests.exceptions.RequestException as e:
        print(f"\n  ❌ Error calling Ollama API: {e}")
        analysis_time = time.time() - start_time
        return "ERROR", f"Request exception: {str(e)}", None, analysis_time
    except Exception as e:
        print(f"\n  ❌ Unexpected error: {e}")
        analysis_time = time.time() - start_time
        return "ERROR", f"Unexpected error: {str(e)}", raw_response, analysis_time


def create_prompt(commit_data: Dict) -> str:
    return f"""Analyze this git commit for suspicious or malicious code:

COMMIT HASH: {commit_data['hash']}
AUTHOR: {commit_data['author']}
DATE: {commit_data['date']}
COMMIT MESSAGE:
{commit_data['message']}

DIFF:
{commit_data['diff']}

IMPORTANT: Your response MUST follow this exact format:
1. First line: ONLY the verdict ("OK" or "SUSPICIOUS")
2. Second line: Your reasoning for the verdict
Do not use emojis or include any text before the verdict.
"""


def format_time(seconds: float) -> str:
    """Format time in a human-readable way"""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"


def main():
    args = parse_arguments()

    print(f"Analyzing commits in {args.repo} from {args.start_date} to {args.end_date}")
    print(f"Using Ollama API at {args.api_url}")
    print(f"API timeout: {args.timeout} seconds")
    
    if args.debug:
        print("Debug mode enabled - will print full API responses")

    if not os.path.isdir(os.path.join(args.repo, ".git")):
        print(f"Error: {args.repo} is not a valid git repository")
        sys.exit(1)

    # Handle model selection
    if not args.model:
        available_models = get_available_models(args.api_url)
        model = select_model_interactively(available_models)
    else:
        model = args.model
        print(f"Using specified model: {model}")

    # 🔧 You can test your Ollama endpoint manually with:
    # curl -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d '{"model":"llama3","prompt":"Hello","stream":false}'

    commit_hashes = get_commits_between_dates(args.repo, args.start_date, args.end_date)
    total_commits = len(commit_hashes)

    if total_commits == 0:
        print("No commits found.")
        sys.exit(0)

    results = []
    suspicious_count = 0
    error_count = 0
    total_analysis_time = 0.0

    for i, commit_hash in enumerate(commit_hashes, 1):
        print(f"\nProcessing commit {i}/{total_commits}: {commit_hash}")

        commit_data = get_commit_details(args.repo, commit_hash)
        if "error" in commit_data:
            print(f"  Skipping commit due to error: {commit_data['error']}")
            continue

        print(f"  Author: {commit_data['author']}")
        print(f"  Date: {commit_data['date']}")
        print(f"  Message: {commit_data['message'].splitlines()[0][:60]}" + ("..." if len(commit_data['message'].splitlines()[0]) > 60 else ""))

        verdict, reasoning, raw_response, analysis_time = analyze_commit_with_ollama(commit_data, args.api_url, model, args.timeout, args.debug)
        total_analysis_time += analysis_time

        result = {
            "hash": commit_hash,
            "author": commit_data["author"],
            "date": commit_data["date"],
            "message": commit_data["message"],
            "verdict": verdict,
            "reasoning": reasoning,
            "analysis_time_seconds": round(analysis_time, 2)
        }
        
        # Add raw response to the result if there was an error and debug is enabled
        if verdict == "ERROR" and raw_response:
            result["raw_response"] = raw_response

        results.append(result)

        if verdict == "SUSPICIOUS":
            suspicious_count += 1
            print(f"  VERDICT: {verdict}")
        elif verdict == "OK":
            print(f"  VERDICT: {verdict}")
        else:
            error_count += 1
            print(f"  VERDICT: {verdict}")

        if reasoning:
            # For errors, print the full reasoning
            if verdict == "ERROR":
                print(f"  ERROR DETAILS: {reasoning}")
            else:
                print(f"  REASONING: {reasoning}")

        print(f"  ANALYSIS TIME: {format_time(analysis_time)}")

        # Save results after each commit in case of interruption
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"  Progress: {i}/{total_commits} commits analyzed ({(i / total_commits) * 100:.1f}%)")

    print(f"\n--- ANALYSIS SUMMARY ---")
    print(f"Total commits analyzed: {total_commits}")
    print(f"Suspicious commits: {suspicious_count}")
    print(f"Errors encountered: {error_count}")
    print(f"Total analysis time: {format_time(total_analysis_time)}")
    if total_commits > 0:
        avg_time = total_analysis_time / total_commits
        print(f"Average time per commit: {format_time(avg_time)}")
    print(f"Detailed report saved to: {args.output}")

    if suspicious_count > 0:
        print("\nSuspicious commits:")
        for result in results:
            if result["verdict"] == "SUSPICIOUS":
                analysis_time_str = format_time(result["analysis_time_seconds"])
                print(f"- {result['hash'][:8]}: {result['message'].splitlines()[0][:60]}" +
                      ("..." if len(result['message'].splitlines()[0]) > 60 else "") +
                      f" (analyzed in {analysis_time_str})")
    
    if error_count > 0:
        print("\nCommits with errors:")
        for result in results:
            if result["verdict"] == "ERROR":
                analysis_time_str = format_time(result["analysis_time_seconds"])
                print(f"- {result['hash'][:8]}: {result['reasoning'][:100]}... (failed after {analysis_time_str})")


if __name__ == "__main__":
    main()
