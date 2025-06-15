import os
import re
import subprocess
from datetime import datetime
from dateutil import parser

def normalize_date_to_short_format(date_input):
    """
    Convert any date format to YYYY-MM-dd format.
    
    Args:
        date_input: Can be string, datetime object, or timestamp
    
    Returns:
        str: Date in YYYY-MM-dd format, or None if parsing fails
    """
    if date_input is None or date_input == '':
        return None
    
    try:
        # Handle datetime objects
        if isinstance(date_input, datetime):
            return date_input.strftime('%Y-%m-%d')
        
        # Handle Unix timestamps
        elif isinstance(date_input, (int, float)):
            if date_input > 1e10:  # Likely milliseconds
                date_input = date_input / 1000
            dt = datetime.fromtimestamp(date_input)
            return dt.strftime('%Y-%m-%d')
        
        # Handle strings
        elif isinstance(date_input, str):
            date_str = date_input.strip()
            
            # Clean common issues
            date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)  # Remove ordinals
            date_str = re.sub(r'\s+', ' ', date_str)  # Normalize whitespace
            
            # Use dateutil parser (handles most formats automatically)
            dt = parser.parse(date_str, fuzzy=True)
            return dt.strftime('%Y-%m-%d')
        
        return None
        
    except Exception:
        return None

# Example usage
def test_date_normalization():
    test_dates = [
        "2023-12-25",
        "12/25/2023", 
        "Dec 25, 2023",
        "December 25th, 2023",
        "2023/12/25",
        "20231225",
        datetime(2023, 12, 25),
        1703462400,  # Unix timestamp
        "2023-1-5",
        "Jan 5 2023",
        "",
        None,
        "invalid date"
    ]
    
    for date_input in test_dates:
        result = normalize_date_to_short_format(date_input)
        print(f"Input: {date_input} -> Output: {result}")

def get_repo_name_from_git(repo_path: str) -> str:
    """Extract repository name from git remote URL."""
    try:
        original_cwd = os.getcwd()
        os.chdir(repo_path)
        
        # Try to get remote URL
        result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                              capture_output=True, text=True, check=True)
        remote_url = result.stdout.strip()
        
        # Extract repo name from various URL formats
        # Examples:
        # https://github.com/user/repo.git -> repo
        # git@github.com:user/repo.git -> repo
        # https://github.com/user/repo -> repo
        
        if remote_url:
            # Remove .git suffix if present
            if remote_url.endswith('.git'):
                remote_url = remote_url[:-4]
            
            # Extract the last part after / or :
            repo_name = remote_url.split('/')[-1].split(':')[-1]
            return repo_name
            
    except Exception:
        pass
    finally:
        os.chdir(original_cwd)
    
    # Fallback to directory name
    return os.path.basename(os.path.abspath(repo_path))