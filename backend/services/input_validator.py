"""
Input Validation & Sanitization
Prevents malicious inputs and abuse
"""
from typing import Optional, Set
from urllib.parse import urlparse
from pathlib import Path, PurePosixPath
import re
import os
import ipaddress
import socket


class InputValidator:
    """Validate and sanitize user inputs"""
    
    # Allowed Git URL schemes
    ALLOWED_SCHEMES = {'http', 'https', 'git', 'ssh'}
    
    # Allowed Git hosts (configurable via ALLOWED_GIT_HOSTS env var)
    # Default: major public Git hosting providers only
    DEFAULT_ALLOWED_HOSTS = {
        'github.com',
        'gitlab.com',
        'bitbucket.org',
        'codeberg.org',
        'sr.ht',  # sourcehut
    }
    
    # Shell metacharacters that could enable command injection
    # These should NEVER appear in a legitimate Git URL
    COMMAND_INJECTION_CHARS = {
        ';',    # Command separator
        '&&',   # AND operator
        '||',   # OR operator
        '|',    # Pipe
        '`',    # Backtick execution
        '$(',   # Subshell
        '${',   # Variable expansion
        '\n',   # Newline
        '\r',   # Carriage return
        '\x00', # Null byte
    }
    
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
    MAX_GIT_URL_LENGTH = 500
    MAX_FUNCTIONS_PER_REPO = 50000  # Prevent indexing chromium-sized repos
    MAX_REPOS_PER_USER = 50
    
    @staticmethod
    def _get_allowed_hosts() -> Set[str]:
        """Get allowed Git hosts from environment or use defaults."""
        env_hosts = os.environ.get('ALLOWED_GIT_HOSTS', '')
        if env_hosts:
            # Parse comma-separated list from env
            return {h.strip().lower() for h in env_hosts.split(',') if h.strip()}
        return InputValidator.DEFAULT_ALLOWED_HOSTS
    
    @staticmethod
    def _contains_injection_chars(url: str) -> Optional[str]:
        """Check if URL contains shell injection characters."""
        for char in InputValidator.COMMAND_INJECTION_CHARS:
            if char in url:
                return f"URL contains forbidden character: {repr(char)}"
        return None
    
    @staticmethod
    def _is_private_ip(hostname: str) -> bool:
        """
        Check if hostname resolves to a private/reserved IP address.
        Prevents SSRF attacks targeting internal networks.
        """
        # Direct IP check first
        try:
            ip = ipaddress.ip_address(hostname)
            return (
                ip.is_private or
                ip.is_loopback or
                ip.is_link_local or
                ip.is_multicast or
                ip.is_reserved or
                ip.is_unspecified
            )
        except ValueError:
            pass  # Not a direct IP, continue with hostname check
        
        # Known dangerous hostnames
        dangerous_hostnames = {
            'localhost',
            'localhost.localdomain',
            'ip6-localhost',
            'ip6-loopback',
        }
        if hostname.lower() in dangerous_hostnames:
            return True
        
        # Check for AWS/cloud metadata endpoints
        metadata_hosts = {
            '169.254.169.254',  # AWS/GCP metadata
            'metadata.google.internal',
            'metadata.internal',
        }
        if hostname.lower() in metadata_hosts:
            return True
        
        # Try to resolve hostname and check resulting IP
        # Only do this as a final check - don't want to slow down validation
        try:
            resolved_ip = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(resolved_ip)
            return (
                ip.is_private or
                ip.is_loopback or
                ip.is_link_local or
                ip.is_reserved
            )
        except (socket.gaierror, socket.herror, ValueError):
            # Can't resolve - will fail at clone anyway
            # Don't block, let git handle it
            pass
        
        return False
    
    @staticmethod
    def _extract_host_from_ssh_url(ssh_url: str) -> Optional[str]:
        """Extract hostname from SSH URL format (git@host:user/repo.git)."""
        # Format: git@github.com:user/repo.git
        if not ssh_url.startswith('git@'):
            return None
        
        # Split off 'git@' and get the host part before ':'
        remainder = ssh_url[4:]  # Remove 'git@'
        if ':' not in remainder:
            return None
        
        host = remainder.split(':')[0].lower()
        return host
    
    @staticmethod
    def validate_git_url(git_url: str) -> tuple[bool, Optional[str]]:
        """
        Validate Git URL is safe to clone.
        
        Security checks:
        1. Length limits
        2. Command injection character detection
        3. Scheme validation (https preferred)
        4. Host allowlist (github, gitlab, bitbucket by default)
        5. Private IP / SSRF prevention
        6. URL format validation
        """
        # Check length
        if not git_url:
            return False, "Git URL cannot be empty"
        if len(git_url) > InputValidator.MAX_GIT_URL_LENGTH:
            return False, f"Git URL too long (max {InputValidator.MAX_GIT_URL_LENGTH} characters)"
        
        # CRITICAL: Check for command injection characters FIRST
        # This must happen before any parsing
        injection_error = InputValidator._contains_injection_chars(git_url)
        if injection_error:
            return False, f"Invalid Git URL: {injection_error}"
        
        allowed_hosts = InputValidator._get_allowed_hosts()
        
        try:
            # Handle SSH URLs (git@github.com:user/repo.git)
            if git_url.startswith('git@'):
                host = InputValidator._extract_host_from_ssh_url(git_url)
                if not host:
                    return False, "Invalid SSH URL format. Expected: git@host:owner/repo.git"
                
                # Check against allowlist
                if host not in allowed_hosts:
                    return False, f"Host '{host}' not in allowed list. Allowed: {', '.join(sorted(allowed_hosts))}"
                
                # Validate format: git@host:owner/repo[.git]
                ssh_pattern = r'^git@[\w.-]+:[\w.-]+/[\w.-]+(?:\.git)?$'
                if not re.match(ssh_pattern, git_url):
                    return False, "Invalid SSH URL format. Expected: git@host:owner/repo.git"
                
                return True, None
            
            # Parse HTTP(S) URLs
            parsed = urlparse(git_url)
            
            # Check scheme - prefer HTTPS
            if parsed.scheme not in {'http', 'https'}:
                return False, f"Invalid URL scheme '{parsed.scheme}'. Only http and https are allowed for clone URLs"
            
            # Must have a hostname
            if not parsed.netloc:
                return False, "Invalid URL: missing hostname"
            
            # Extract hostname (remove port if present)
            hostname = parsed.netloc.split(':')[0].lower()
            
            # Check against allowlist
            if hostname not in allowed_hosts:
                return False, f"Host '{hostname}' not in allowed list. Allowed: {', '.join(sorted(allowed_hosts))}"
            
            # Check for private IP / SSRF
            if InputValidator._is_private_ip(hostname):
                return False, "Private/internal network URLs are not allowed"
            
            # Validate URL path format: /owner/repo[.git]
            # Must have at least owner and repo
            path = parsed.path
            if not path or path == '/':
                return False, "Invalid repository URL: missing owner/repo path"
            
            # Path should be /owner/repo or /owner/repo.git
            path_pattern = r'^/[\w.-]+/[\w.-]+(?:\.git)?(?:/.*)?$'
            if not re.match(path_pattern, path):
                return False, "Invalid repository URL format. Expected: https://host/owner/repo"
            
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
        
        # Normalize path without filesystem access to prevent traversal
        # Use os.path.normpath which resolves .. and . without touching filesystem
        normalized = os.path.normpath(file_path)
        
        # After normalization, path should not start with .. or be absolute
        if normalized.startswith('..') or os.path.isabs(normalized):
            return False, "Path escapes allowed directory"
        
        # If repo_root provided, do additional containment check
        if repo_root:
            try:
                # Use PurePosixPath for safe path manipulation without filesystem access
                # This avoids the CodeQL "uncontrolled data in path" warning
                safe_root = os.path.normpath(repo_root)
                safe_full = os.path.normpath(os.path.join(safe_root, normalized))
                
                # Ensure the joined path stays within repo_root
                if not safe_full.startswith(safe_root + os.sep) and safe_full != safe_root:
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
