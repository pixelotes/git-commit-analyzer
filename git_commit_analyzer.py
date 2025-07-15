#!/usr/bin/env python3
"""
Git Commit Security Analyzer with External Prompt Support
A Python tool that analyzes git commits for suspicious or malicious code changes using AI-powered analysis through Ollama.
Enhanced with support for external custom prompts.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import requests


class GitCommitAnalyzer:
    def __init__(self, repo_path: str, api_url: str = "http://localhost:11434/api/generate", 
                 timeout: int = 120, debug: bool = False, prompt_file: Optional[str] = None):
        self.repo_path = repo_path
        self.api_url = api_url
        self.timeout = timeout
        self.debug = debug
        self.prompt_file = prompt_file
        self.default_prompt = self._get_default_prompt()
        self.custom_prompt = self._load_custom_prompt() if prompt_file else None
        
    def _get_default_prompt(self) -> str:
        """Get the default security analysis prompt."""
        return """You are a security expert analyzing git commit diffs for potentially malicious or suspicious code changes.

Analyze the following git commit diff and determine if it contains any suspicious or malicious patterns:

COMMIT INFORMATION:
- Hash: {hash}
- Author: {author}
- Date: {date}
- Message: {message}

DIFF:
{diff}

INSTRUCTIONS:

Look for:
- Suspicious code patterns (obfuscated code, unusual encodings)
- Potential security vulnerabilities (SQL injection, XSS, command injection)
- Malicious code injection (backdoors, unauthorized access mechanisms)
- Unusual or suspicious file operations
- Network requests to suspicious domains
- Credential harvesting or data exfiltration attempts
- Code that appears to be intentionally hidden or obfuscated


If the commit appears safe and contains normal development changes, respond with PASS.
If the commit contains potentially suspicious or malicious changes, respond with FAIL.

OUTPUT:
Anwer only with these two lines:
VERDICT: PASS or FAIL
REASONING: Brief explanation of your analysis, one or two sentences max."""

    
    def get_repo_name_from_git(self) -> str:
        """Get the actual repository name from the git config."""
        try:
            original_cwd = os.getcwd()
            os.chdir(self.repo_path)
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True, text=True, check=True
            )
            os.chdir(original_cwd)
            url = result.stdout.strip()
            if url.endswith(".git"):
                url = url[:-4]
            return os.path.basename(url)
        except Exception:
            return os.path.basename(os.path.abspath(self.repo_path))

    
    def _load_custom_prompt(self) -> Optional[str]:
        """Load custom prompt from external file."""
        try:
            if not os.path.exists(self.prompt_file):
                print(f"Warning: Prompt file '{self.prompt_file}' not found. Using default prompt.")
                return None
                
            with open(self.prompt_file, 'r', encoding='utf-8') as f:
                prompt = f.read().strip()
                
            if not prompt:
                print(f"Warning: Prompt file '{self.prompt_file}' is empty. Using default prompt.")
                return None
                
            print(f"Loaded custom prompt from: {self.prompt_file}")
            return prompt
            
        except Exception as e:
            print(f"Error loading prompt file '{self.prompt_file}': {e}")
            print("Using default prompt instead.")
            return None

    def get_active_prompt(self) -> str:
        """Get the currently active prompt (custom or default)."""
        return self.custom_prompt if self.custom_prompt else self.default_prompt

    def get_available_models(self) -> List[str]:
        """Get list of available Ollama models."""
        try:
            response = requests.get(f"{self.api_url.replace('/api/generate', '/api/tags')}", timeout=10)
            response.raise_for_status()
            models = response.json().get('models', [])
            return [model['name'] for model in models]
        except Exception as e:
            if self.debug:
                print(f"Error querying available models: {e}")
            return []

    def select_model(self, model_name: Optional[str] = None) -> str:
        """Select model to use for analysis."""
        models = self.get_available_models()
        
        if not models:
            print("Error: No Ollama models found. Please ensure Ollama is running and has models installed.")
            sys.exit(1)
            
        if len(models) == 1:
            selected_model = models[0]
            print(f"Using single available model: {selected_model}")
            return selected_model
            
        if model_name:
            if model_name in models:
                print(f"Using specified model: {model_name}")
                return model_name
            else:
                print(f"Warning: Model '{model_name}' not found in available models.")
                print("Available models:")
                for i, model in enumerate(models, 1):
                    print(f"  {i}. {model}")
                print(f"Falling back to interactive selection...")

        # Interactive model selection
        print("\nAvailable Ollama models:")
        for i, model in enumerate(models, 1):
            print(f"  {i}. {model}")
            
        while True:
            try:
                choice = input(f"\nSelect model (1-{len(models)}): ").strip()
                index = int(choice) - 1
                if 0 <= index < len(models):
                    selected_model = models[index]
                    print(f"Selected model: {selected_model}")
                    return selected_model
                else:
                    print(f"Please enter a number between 1 and {len(models)}")
            except (ValueError, KeyboardInterrupt):
                print("\nExiting...")
                sys.exit(1)

    def get_commits_in_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Get commits in the specified date range."""
        try:
            # Change to repo directory
            original_cwd = os.getcwd()
            os.chdir(self.repo_path)
            
            # Get commits in date range with format: hash|author|date|subject
            cmd = [
                'git', 'log',
                f'--since={start_date}',
                f'--until={end_date}',
                '--pretty=format:%H|%an <%ae>|%ai|%s',
                '--no-merges'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            os.chdir(original_cwd)
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 3)
                    if len(parts) == 4:
                        commits.append({
                            'hash': parts[0],
                            'author': parts[1],
                            'date': parts[2],
                            'message': parts[3]
                        })
            
            return commits
            
        except subprocess.CalledProcessError as e:
            print(f"Error getting commits: {e}")
            return []
        except Exception as e:
            print(f"Error: {e}")
            return []

    def get_commit_diff(self, commit_hash: str) -> str:
        """Get the diff for a specific commit."""
        try:
            original_cwd = os.getcwd()
            os.chdir(self.repo_path)
            
            cmd = ['git', 'show', '--format=', commit_hash]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            os.chdir(original_cwd)
            return result.stdout
            
        except subprocess.CalledProcessError as e:
            if self.debug:
                print(f"Error getting diff for {commit_hash}: {e}")
            return ""
        except Exception as e:
            if self.debug:
                print(f"Error: {e}")
            return ""

    def analyze_commit_with_ollama(self, commit: Dict, model: str) -> Tuple[str, str, float]:
        """Analyze a commit using Ollama."""
        diff = self.get_commit_diff(commit['hash'])
        
        if not diff:
            return "ERROR", "Could not retrieve commit diff", 0.0
            
        # Format prompt with commit information
        prompt = self.get_active_prompt().format(
            hash=commit['hash'],
            author=commit['author'],
            date=commit['date'],
            message=commit['message'],
            diff=diff
        )
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        start_time = time.time()
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            analysis_time = time.time() - start_time
            
            result = response.json()
            ai_response = result.get('response', '').strip()
            
            # Parse response
            verdict = "ERROR"
            reasoning = "Could not parse AI response"
            
            # Save response.json() to a directory named after the repository
            repo_dir_name = os.path.basename(os.path.abspath(self.repo_path))
            save_dir = os.path.join(os.getcwd(), repo_dir_name)
            os.makedirs(save_dir, exist_ok=True)
            if self.debug:
                with open(os.path.join(save_dir, f"{commit['hash']}.json"), "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

            lines = ai_response.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('VERDICT:'):
                    verdict_text = line.replace('VERDICT:', '').strip().upper()
                    if verdict_text in ['PASS', 'FAIL']:
                        verdict = verdict_text
                elif line.startswith('REASONING:'):
                    reasoning = line.replace('REASONING:', '').strip()
                    
            return verdict, reasoning, analysis_time
            
        except requests.exceptions.Timeout:
            return "ERROR", f"Request timeout after {self.timeout} seconds", time.time() - start_time
        except Exception as e:
            return "ERROR", f"Analysis failed: {str(e)}", time.time() - start_time

    def analyze_commits(self, start_date: str, end_date: str, model: str, output_file: str):
        """Analyze all commits in the specified range."""
        print(f"Analyzing commits from {start_date} to {end_date}")
        print(f"Using model: {model}")
        if self.custom_prompt:
            print(f"Using custom prompt from: {self.prompt_file}")
        else:
            print("Using default security analysis prompt")
        print(f"Repository: {self.repo_path}")
        print(f"Output file: {output_file}")
        print("-" * 60)
        
        commits = self.get_commits_in_range(start_date, end_date)
        
        if not commits:
            print("No commits found in the specified date range.")
            return
            
        print(f"Found {len(commits)} commits to analyze\n")
        
        results = []
        total_analysis_time = 0
        
        for i, commit in enumerate(commits, 1):
            print(f"Processing commit {i}/{len(commits)}: {commit['hash'][:12]}")
            print(f"Author: {commit['author']}")
            print(f"Date: {commit['date']}")
            print(f"Message: {commit['message']}")
            
            print("Sending to Ollama for analysis...", end=' ', flush=True)
            
            verdict, reasoning, analysis_time = self.analyze_commit_with_ollama(commit, model)
            total_analysis_time += analysis_time
            
            print(f"received response.")
            print(f"VERDICT: {verdict}")
            print(f"REASONING: {reasoning}")
            print(f"ANALYSIS TIME: {analysis_time:.1f}s")
            
            result = {
                'hash': commit['hash'],
                'author': commit['author'],
                'date': commit['date'],
                'message': commit['message'],
                'verdict': verdict,
                'reasoning': reasoning,
                'analysis_time_seconds': round(analysis_time, 2)
            }
            
            results.append(result)
            
            progress = (i / len(commits)) * 100
            print(f"Progress: {i}/{len(commits)} commits analyzed ({progress:.1f}%)")
            print("-" * 60)
        
        # Add summary statistics
        pass_count = sum(1 for r in results if r['verdict'] == 'PASS')
        fail_count = sum(1 for r in results if r['verdict'] == 'FAIL')
        error_count = sum(1 for r in results if r['verdict'] == 'ERROR')
        avg_analysis_time = total_analysis_time / len(results) if results else 0
        
        summary = {
            'analysis_summary': {
                'total_commits': len(results),
                'pass_count': pass_count,
                'fail_count': fail_count,
                'error_count': error_count,
                'total_analysis_time_seconds': round(total_analysis_time, 2),
                'average_analysis_time_seconds': round(avg_analysis_time, 2),
                'model_used': model,
                'prompt_type': 'custom' if self.custom_prompt else 'default',
                'prompt_file': self.prompt_file if self.custom_prompt else None,
                'analysis_date': datetime.now().isoformat(),
                'date_range': {
                    'start': start_date,
                    'end': end_date
                }
            },
            'commits': results
        }
        
        # Save results
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            print(f"\n✅ Analysis complete! Results saved to: {output_file}")
        except Exception as e:
            print(f"\n❌ Error saving results: {e}")
            return
            
        # Print summary
        print(f"\n📊 ANALYSIS SUMMARY:")
        print(f"   Total commits analyzed: {len(results)}")
        print(f"   PASS: {pass_count}")
        print(f"   FAIL: {fail_count}")
        print(f"   ERROR: {error_count}")
        print(f"   Total analysis time: {total_analysis_time:.1f}s")
        print(f"   Average time per commit: {avg_analysis_time:.1f}s")
        
        if fail_count > 0:
            print(f"\n⚠️  {fail_count} commits flagged for review:")
            for result in results:
                if result['verdict'] == 'FAIL':
                    print(f"   - {result['hash'][:12]}: {result['message'][:50]}...")


def create_sample_prompt_file(filename: str = "custom_prompt.txt"):
    """Create a sample custom prompt file."""
    sample_prompt = """You are an expert code reviewer analyzing git commit diffs.

COMMIT DETAILS:
- Hash: {hash}
- Author: {author}
- Date: {date}
- Message: {message}

CODE CHANGES:
{diff}

Please analyze this commit for:
1. Code quality issues
2. Potential bugs or vulnerabilities
3. Security concerns
4. Best practice violations

Focus specifically on:
- Input validation
- Authentication/authorization issues
- Data handling and storage
- Network communications
- File operations

Provide your assessment:
VERDICT: PASS or FAIL
REASONING: Detailed explanation of your findings

Use PASS for normal, safe changes and FAIL for potentially problematic changes."""
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(sample_prompt)
        print(f"Sample prompt file created: {filename}")
        print("You can modify this file to customize the analysis prompt.")
    except Exception as e:
        print(f"Error creating sample prompt file: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze git commits for suspicious or malicious code changes using AI (Ollama)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with interactive model selection
  python git_commit_analyzer.py --repo /path/to/repo --start-date "2024-01-01" --end-date "2024-01-31"
  
  # With specific model
  python git_commit_analyzer.py --repo /path/to/repo --start-date "2024-01-01" --end-date "2024-01-31" --model "qwen2.5-coder:7b"
  
  # With custom prompt file
  python git_commit_analyzer.py --repo /path/to/repo --start-date "2024-01-01" --end-date "2024-01-31" --prompt custom_security_prompt.txt
  
  # Create sample prompt file
  python git_commit_analyzer.py --create-sample-prompt
  
  # With all options
  python git_commit_analyzer.py \\
    --repo /path/to/repo \\
    --start-date "2024-01-01" \\
    --end-date "2024-01-31" \\
    --model "qwen2.5-coder:7b" \\
    --prompt my_custom_prompt.txt \\
    --output detailed_analysis.json \\
    --timeout 180 \\
    --slack-webhook "https://hooks.slack.com/xxx" \\
    --debug
        """
    )
    
    parser.add_argument('--repo', type=str, required=False,
                      help='Path to the git repository')
    parser.add_argument('--start-date', type=str, required=False,
                      help='Start date in YYYY-MM-DD format')
    parser.add_argument('--end-date', type=str, required=False,
                      help='End date in YYYY-MM-DD format')
    parser.add_argument('--model', type=str,
                      help='Ollama model to use (if not specified, shows interactive selection)')
    parser.add_argument('--api-url', type=str, default="http://localhost:11434/api/generate",
                      help='Ollama API URL (default: http://localhost:11434/api/generate)')
    parser.add_argument('--output', type=str,
                      help='Output JSON file path (default: {repo-name}-report.json)')
    parser.add_argument('--timeout', type=int, default=120,
                      help='API request timeout in seconds (default: 120)')
    parser.add_argument('--debug', action='store_true',
                      help='Enable detailed debug output')
    parser.add_argument('--prompt', type=str,
                      help='Path to custom prompt file (uses default security prompt if not specified)')
    parser.add_argument('--create-sample-prompt', action='store_true',
                      help='Create a sample custom prompt file and exit')
    parser.add_argument('--slack-webhook', type=str, required=False,
                      help='Posts the end results to a Slack channel using a webhook URL')
    
    args = parser.parse_args()
    
    # Handle sample prompt creation
    if args.create_sample_prompt:
        create_sample_prompt_file()
        return
    
    # Validate required arguments
    if not args.repo or not args.start_date:
        parser.error("--repo and --start-date are required (unless using --create-sample-prompt)")
    
    # Validate end date
    if not args.end_date:
        args.end_date = datetime.now().strftime("%Y-%m-%d")

    # Validate repository path
    if not os.path.exists(args.repo):
        print(f"Error: Repository path '{args.repo}' does not exist.")
        sys.exit(1)
        
    if not os.path.exists(os.path.join(args.repo, '.git')):
        print(f"Error: '{args.repo}' is not a git repository.")
        sys.exit(1)
    
    # Set output file if not specified
    if not args.output:
        repo_name = os.path.basename(os.path.abspath(args.repo))
        args.output = f"{repo_name}-report.json"
    
    # Validate custom prompt file if specified
    if args.prompt and not os.path.exists(args.prompt):
        print(f"Warning: Custom prompt file '{args.prompt}' not found.")
        choice = input("Continue with default prompt? (y/N): ").strip().lower()
        if choice != 'y':
            print("Exiting...")
            sys.exit(1)
        args.prompt = None
    
    try:
        # Initialize analyzer
        analyzer = GitCommitAnalyzer(
            repo_path=args.repo,
            api_url=args.api_url,
            timeout=args.timeout,
            debug=args.debug,
            prompt_file=args.prompt
        )
        
        # Select model
        model = analyzer.select_model(args.model)
        
        # Run analysis
        analyzer.analyze_commits(args.start_date, args.end_date, model, args.output)

        # Post results to Slack if webhook is provided
        if args.slack_webhook:
            try:
                with open(args.output, 'r', encoding='utf-8') as f:
                    report = json.load(f)
                
                # Build flagged commits list
                repo_name = analyzer.get_repo_name_from_git()
                
                # Try to get remote URL to build commit links
                try:
                    original_cwd = os.getcwd()
                    os.chdir(args.repo)
                    remote_url = subprocess.run(
                        ["git", "config", "--get", "remote.origin.url"],
                        capture_output=True, text=True, check=True
                    ).stdout.strip()
                    os.chdir(original_cwd)
                
                    # Normalize GitHub URL (remove .git, convert SSH to HTTPS)
                    if remote_url.endswith(".git"):
                        remote_url = remote_url[:-4]
                    if remote_url.startswith("git@github.com:"):
                        remote_url = "https://github.com/" + remote_url[len("git@github.com:"):]
                except Exception:
                    remote_url = None
                
                flagged_commits = []
                for commit in report['commits']:
                    if commit['verdict'] in ['FAIL', 'ERROR']:
                        commit_hash = commit['hash'][:8]
                        message_snippet = commit['message'][:60] + ('...' if len(commit['message']) > 60 else '')
                        if remote_url:
                            commit_url = f"{remote_url}/commit/{commit['hash']}"
                            line = f"• <{commit_url}|{commit_hash}> - {commit['verdict']}: {message_snippet}"
                        else:
                            line = f"• {commit_hash} - {commit['verdict']}: {message_snippet}"
                        flagged_commits.append(line)
                
                flagged_text = "\n".join(flagged_commits) if flagged_commits else "None"
                
                slack_payload = {
                    "text": f"Git Commit Analysis Report for {analyzer.get_repo_name_from_git()}:\n"
                            f"---\n"
                            f"Analysis date: {report['analysis_summary']['analysis_date']}\n"
                            f"Total Commits: {report['analysis_summary']['total_commits']}\n"
                            f"Pass: {report['analysis_summary']['pass_count']}, "
                            f"Fail: {report['analysis_summary']['fail_count']}, "
                            f"Errors: {report['analysis_summary']['error_count']}\n\n"
                            f"Flagged Commits:\n{flagged_text}\n\n"
                            f"Total analysis time: {report['analysis_summary']['total_analysis_time_seconds']}\n"
                            f"Average time per commit: {report['analysis_summary']['average_analysis_time_seconds']}\n"
                            f"Report saved to: {args.output}"
                }
                response = requests.post(args.slack_webhook, json=slack_payload)
                response.raise_for_status()
                print("Results posted to Slack successfully.")
            except Exception as e:
                print(f"Error posting results to Slack: {e}")
        
    except KeyboardInterrupt:
        print("\n\nAnalysis interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
