"""
Input Validation & Sanitization
Prevents malicious inputs and abuse
"""
from typing import Optional
from urllib.parse import urlparse
from pathlib import Path
import re


class InputValidator:
    """Validate and sanitize user inputs"""
    
    # Allowed Git URL schemes
    ALLOWED_SCHEMES = {'http', 'https', 'git', 'ssh'}
    
    # Dangerous path patterns
    DANGEROUS_PATTERNS = [
        '..',           # Path traversal
        '~',            # Home directory
        '/etc/',        # System files
        '/var/',        # System files
        '/usr/',        # System binaries
        'C:\\',         # Windows system
        '\\\\',         # UNC paths
    ]
    
    # Max sizes
    MAX_QUERY_LENGTH = 500
    MAX_FILE_PATH_LENGTH = 500
    MAX_REPO_NAME_LENGTH = 100
    MAX_FUNCTIONS_PER_REPO = 50000  # Prevent indexing chromium-sized repos
    MAX_REPOS_PER_USER = 50
    
    @staticmethod
    def validate_git_url(git_url: str) -> tuple[bool, Optional[str]]:
        """Validate Git URL is safe"""
        if not git_url or len(git_url) > 500:
            return False, "Git URL too long or empty"
        
        try:
            # Handle SSH URLs (git@github.com:user/repo.git)
            if git_url.startswith('git@'):
                # SSH URL format - basic validation
                if ':' not in git_url or '/' not in git_url:
                    return False, "Invalid SSH URL format"
                # Block localhost/private
                if any(host in git_url.lower() for host in ['localhost', '127.0.0.1', '0.0.0.0']):
                    return False, "Private/local URLs are not allowed"
                return True, None
            
            parsed = urlparse(git_url)
            
            # Check scheme
            if parsed.scheme not in InputValidator.ALLOWED_SCHEMES:
                return False, f"Invalid URL scheme. Allowed: {InputValidator.ALLOWED_SCHEMES}"
            
            # Prevent file:// and other dangerous schemes
            if parsed.scheme in {'file', 'ftp', 'data'}:
                return False, "File and FTP URLs are not allowed"
            
            # Must have a hostname for http/https
            if parsed.scheme in {'http', 'https'} and not parsed.netloc:
                return False, "Invalid URL format"
            
            # Prevent localhost/private IPs (basic check)
            if any(host in parsed.netloc.lower() for host in ['localhost', '127.0.0.1', '0.0.0.0', '169.254']):
                return False, "Private/local URLs are not allowed"
            
            return True, None
            
        except Exception as e:
            return False, f"Invalid URL format: {str(e)}"
    
    @staticmethod
    def validate_file_path(file_path: str, repo_root: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """Validate file path is safe and within repository"""
        if not file_path or len(file_path) > InputValidator.MAX_FILE_PATH_LENGTH:
            return False, "File path too long or empty"
        
        # Check for dangerous patterns
        for pattern in InputValidator.DANGEROUS_PATTERNS:
            if pattern in file_path:
                return False, f"Path contains dangerous pattern: {pattern}"
        
        # Must be relative path
        if file_path.startswith('/') or file_path.startswith('\\'):
            return False, "Absolute paths are not allowed"
        
        # Check for null bytes
        if '\x00' in file_path:
            return False, "Null bytes not allowed in paths"
        
        # If repo_root provided, ensure path is within it
        if repo_root:
            try:
                repo_path = Path(repo_root).resolve()
                full_path = (repo_path / file_path).resolve()
                
                # Check if resolved path is still within repo
                if not str(full_path).startswith(str(repo_path)):
                    return False, "Path escapes repository root"
            except Exception:
                return False, "Invalid path format"
        
        return True, None
    
    @staticmethod
    def validate_search_query(query: str) -> tuple[bool, Optional[str]]:
        """Validate search query"""
        if not query:
            return False, "Query cannot be empty"
        
        if len(query) > InputValidator.MAX_QUERY_LENGTH:
            return False, f"Query too long (max {InputValidator.MAX_QUERY_LENGTH} characters)"
        
        # Check for null bytes
        if '\x00' in query:
            return False, "Null bytes not allowed"
        
        # Basic SQL injection prevention
        sql_patterns = ['DROP TABLE', 'DELETE FROM', 'INSERT INTO', 'UPDATE ', '--', ';--']
        query_upper = query.upper()
        for pattern in sql_patterns:
            if pattern in query_upper:
                return False, "Query contains suspicious SQL patterns"
        
        return True, None
    
    @staticmethod
    def validate_repo_name(name: str) -> tuple[bool, Optional[str]]:
        """Validate repository name"""
        if not name or len(name) > InputValidator.MAX_REPO_NAME_LENGTH:
            return False, "Repository name too long or empty"
        
        # Allow alphanumeric, dash, underscore, dot
        if not re.match(r'^[a-zA-Z0-9._-]+$', name):
            return False, "Repository name contains invalid characters"
        
        return True, None
    
    @staticmethod
    def sanitize_string(input_str: str, max_length: int = 500) -> str:
        """Sanitize string input"""
        if not input_str:
            return ""
        
        # Remove null bytes
        sanitized = input_str.replace('\x00', '')
        
        # Truncate if too long
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        # Remove control characters except newline/tab
        sanitized = ''.join(char for char in sanitized if char.isprintable() or char in '\n\t')
        
        return sanitized.strip()


class CostController:
    """Control costs and resource usage"""
    
    def __init__(self, supabase_client):
        self.db = supabase_client
    
    def check_repo_limit(self, user_id: Optional[str], api_key_hash: str) -> tuple[bool, Optional[str]]:
        """Check if user has hit repository limit"""
        # Count repos for this user/key
        if user_id:
            result = self.db.table("repositories").select("id", count="exact").eq("user_id", user_id).execute()
        else:
            result = self.db.table("repositories").select("id", count="exact").eq("api_key_hash", api_key_hash).execute()
        
        count = result.count if hasattr(result, 'count') else len(result.data)
        
        if count >= InputValidator.MAX_REPOS_PER_USER:
            return False, f"Repository limit reached ({InputValidator.MAX_REPOS_PER_USER} max)"
        
        return True, None
    
    def estimate_repo_size(self, repo_path: str) -> int:
        """Estimate number of functions in repository"""
        from pathlib import Path
        
        code_files = []
        extensions = {'.py', '.js', '.jsx', '.ts', '.tsx'}
        skip_dirs = {'node_modules', '.git', '__pycache__', 'venv', 'env', 'dist', 'build'}
        
        try:
            repo_path_obj = Path(repo_path)
            for file_path in repo_path_obj.rglob('*'):
                if file_path.is_dir():
                    continue
                if any(skip in file_path.parts for skip in skip_dirs):
                    continue
                if file_path.suffix in extensions:
                    code_files.append(file_path)
        except Exception:
            return 0
        
        # Estimate ~25 functions per file
        return len(code_files) * 25
    
    def check_repo_size_limit(self, repo_path: str) -> tuple[bool, Optional[str]]:
        """Check if repository is too large to index"""
        estimated_functions = self.estimate_repo_size(repo_path)
        
        if estimated_functions > InputValidator.MAX_FUNCTIONS_PER_REPO:
            return False, f"Repository too large (~{estimated_functions} functions, max {InputValidator.MAX_FUNCTIONS_PER_REPO})"
        
        return True, None
