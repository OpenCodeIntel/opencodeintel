"""
Repository Validator Service
Analyzes repository size before indexing to enforce tier limits.

Part of #94 (repo size limits) implementation.
"""
from pathlib import Path
from dataclasses import dataclass
from typing import Set, Optional
import random

from services.observability import logger
from services.sentry import capture_exception


@dataclass
class RepoAnalysis:
    """Result of repository analysis"""
    file_count: int
    estimated_functions: int
    sampled: bool  # True if we used sampling for large repos
    error: Optional[str] = None  # Error message if analysis failed
    
    @property
    def success(self) -> bool:
        """True if analysis completed without error"""
        return self.error is None
    
    def to_dict(self) -> dict:
        result = {
            "file_count": self.file_count,
            "estimated_functions": self.estimated_functions,
            "sampled": self.sampled,
            "success": self.success,
        }
        if self.error:
            result["error"] = self.error
        return result


class RepoValidator:
    """
    Validates repository size before indexing.
    
    Usage:
        validator = RepoValidator()
        analysis = validator.analyze_repo("/path/to/repo")
        
        # Then check against user limits
        result = user_limits.check_repo_size(
            user_id, 
            analysis.file_count, 
            analysis.estimated_functions
        )
    """
    
    # Code file extensions we index
    CODE_EXTENSIONS: Set[str] = {
        '.py',      # Python
        '.js',      # JavaScript
        '.jsx',     # React
        '.ts',      # TypeScript
        '.tsx',     # React TypeScript
        '.go',      # Go
        '.rs',      # Rust
        '.java',    # Java
        '.rb',      # Ruby
        '.php',     # PHP
        '.c',       # C
        '.cpp',     # C++
        '.h',       # C/C++ headers
        '.hpp',     # C++ headers
        '.cs',      # C#
        '.swift',   # Swift
        '.kt',      # Kotlin
        '.scala',   # Scala
    }
    
    # Directories to skip (common non-code dirs)
    SKIP_DIRS: Set[str] = {
        'node_modules',
        '.git',
        '__pycache__',
        '.pytest_cache',
        'venv',
        'env',
        '.venv',
        '.env',
        'dist',
        'build',
        'target',       # Rust/Java build
        '.next',        # Next.js
        '.nuxt',        # Nuxt.js
        'vendor',       # PHP/Go
        'coverage',
        '.coverage',
        'htmlcov',
        '.tox',
        '.mypy_cache',
        '.ruff_cache',
        'egg-info',
        '.eggs',
    }
    
    # Average functions per file by language (rough estimates)
    # Used for quick estimation without parsing
    AVG_FUNCTIONS_PER_FILE = 25
    
    # Sample size for large repos
    SAMPLE_SIZE = 100
    SAMPLE_THRESHOLD = 500  # Use sampling if more than this many files
    
    # Max file size to read (10MB) - prevent OOM on huge files
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
    
    def __init__(self):
        pass
    
    def analyze_repo(self, repo_path: str) -> RepoAnalysis:
        """
        Analyze repository to count files and estimate functions.
        
        For small repos: counts all files
        For large repos: samples files for speed
        
        Args:
            repo_path: Path to cloned repository
            
        Returns:
            RepoAnalysis with file count and estimated function count
        """
        try:
            # Validate input
            if not repo_path or not isinstance(repo_path, str) or not repo_path.strip():
                logger.warning("Invalid repo_path provided", repo_path=repo_path)
                return RepoAnalysis(
                    file_count=0,
                    estimated_functions=0,
                    sampled=False,
                    error="Invalid repository path: empty or not a string"
                )
            
            # Validate path exists first
            repo_root = Path(repo_path)
            if not repo_root.exists():
                logger.warning("Repo path does not exist", repo_path=repo_path)
                return RepoAnalysis(
                    file_count=0,
                    estimated_functions=0,
                    sampled=False,
                    error=f"Repository path does not exist: {repo_path}"
                )
            
            if not repo_root.is_dir():
                logger.warning("Repo path is not a directory", repo_path=repo_path)
                return RepoAnalysis(
                    file_count=0,
                    estimated_functions=0,
                    sampled=False,
                    error=f"Repository path is not a directory: {repo_path}"
                )
            
            code_files, scan_error = self._find_code_files(repo_path)
            
            # Fail CLOSED if scan had errors (could have undercounted)
            if scan_error:
                logger.error("Repo scan incomplete", repo_path=repo_path, error=scan_error)
                return RepoAnalysis(
                    file_count=len(code_files),
                    estimated_functions=0,
                    sampled=False,
                    error=f"Scan incomplete: {scan_error}"
                )
            
            file_count = len(code_files)
            
            if file_count == 0:
                return RepoAnalysis(
                    file_count=0,
                    estimated_functions=0,
                    sampled=False
                )
            
            # For small repos, estimate directly
            if file_count <= self.SAMPLE_THRESHOLD:
                estimated_functions = file_count * self.AVG_FUNCTIONS_PER_FILE
                return RepoAnalysis(
                    file_count=file_count,
                    estimated_functions=estimated_functions,
                    sampled=False
                )
            
            # For large repos, sample and extrapolate
            sample = random.sample(code_files, min(self.SAMPLE_SIZE, file_count))
            sample_functions = self._count_functions_in_files(sample)
            
            # Extrapolate to full repo
            avg_per_sampled = sample_functions / len(sample)
            estimated_functions = int(avg_per_sampled * file_count)
            
            logger.info(
                "Repo analysis complete (sampled)",
                repo_path=repo_path,
                file_count=file_count,
                sample_size=len(sample),
                estimated_functions=estimated_functions
            )
            
            return RepoAnalysis(
                file_count=file_count,
                estimated_functions=estimated_functions,
                sampled=True
            )
            
        except Exception as e:
            logger.error("Repo analysis failed", repo_path=repo_path, error=str(e))
            capture_exception(e)
            # Return error - caller should fail CLOSED (block indexing)
            return RepoAnalysis(
                file_count=0, 
                estimated_functions=0, 
                sampled=False,
                error=f"Analysis failed: {str(e)}"
            )
    
    def _find_code_files(self, repo_path: str) -> tuple[list[Path], Optional[str]]:
        """
        Find all code files in repository (assumes path validated by caller).
        
        Returns:
            Tuple of (code_files, error_message)
            If error_message is not None, the scan was incomplete
        """
        code_files = []
        repo_root = Path(repo_path)
        scan_error = None
        
        try:
            for file_path in repo_root.rglob('*'):
                # Skip directories
                if file_path.is_dir():
                    continue
                
                # Skip symlinks (security: prevent scanning outside repo)
                if file_path.is_symlink():
                    continue
                
                # Skip files in excluded directories
                if any(skip_dir in file_path.parts for skip_dir in self.SKIP_DIRS):
                    continue
                
                # Check extension
                if file_path.suffix.lower() in self.CODE_EXTENSIONS:
                    code_files.append(file_path)
                    
        except PermissionError as e:
            logger.warning("Permission denied during repo scan", error=str(e))
            scan_error = f"Permission denied: {str(e)}"
        except Exception as e:
            logger.error("Error scanning repo", error=str(e))
            capture_exception(e)
            scan_error = f"Scan failed: {str(e)}"
        
        return code_files, scan_error
    
    def _count_functions_in_files(self, files: list[Path]) -> int:
        """
        Count approximate function definitions in files.
        
        Uses simple heuristics (not full AST parsing) for speed:
        - Python: 'def ' and 'class '
        - JS/TS: 'function ', '=>', 'class '
        - etc.
        
        Security: Skips files larger than MAX_FILE_SIZE_BYTES to prevent OOM.
        """
        total = 0
        
        for file_path in files:
            try:
                # Security: Skip huge files to prevent OOM
                file_size = file_path.stat().st_size
                if file_size > self.MAX_FILE_SIZE_BYTES:
                    logger.debug("Skipping large file", path=str(file_path), size=file_size)
                    total += self.AVG_FUNCTIONS_PER_FILE  # Estimate instead
                    continue
                
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                ext = file_path.suffix.lower()
                
                if ext == '.py':
                    # Count def and class
                    total += content.count('\ndef ') + content.count('\nclass ')
                    # Also count at file start
                    if content.startswith('def ') or content.startswith('class '):
                        total += 1
                        
                elif ext in {'.js', '.jsx', '.ts', '.tsx'}:
                    # Count function declarations and arrows
                    total += content.count('function ')
                    total += content.count('=>')
                    total += content.count('\nclass ')
                    
                elif ext in {'.go'}:
                    total += content.count('\nfunc ')
                    
                elif ext in {'.java', '.cs', '.kt', '.scala'}:
                    # Rough estimate - count method-like patterns
                    total += content.count('public ')
                    total += content.count('private ')
                    total += content.count('protected ')
                    
                elif ext in {'.rb'}:
                    total += content.count('\ndef ')
                    total += content.count('\nclass ')
                    
                elif ext in {'.rs'}:
                    total += content.count('\nfn ')
                    total += content.count('\nimpl ')
                    
                elif ext in {'.c', '.cpp', '.h', '.hpp'}:
                    # Very rough - count open braces after parentheses
                    # This is imprecise but fast
                    total += content.count(') {')
                    
                elif ext == '.php':
                    total += content.count('function ')
                    total += content.count('\nclass ')
                    
                elif ext == '.swift':
                    total += content.count('\nfunc ')
                    total += content.count('\nclass ')
                    
                else:
                    # Default estimate
                    total += self.AVG_FUNCTIONS_PER_FILE
                    
            except Exception:
                # If we can't read a file, use average
                total += self.AVG_FUNCTIONS_PER_FILE
        
        return total
    
    def quick_file_count(self, repo_path: str) -> int:
        """
        Quick file count without full analysis.
        Useful for fast pre-checks.
        """
        files, _ = self._find_code_files(repo_path)
        return len(files)


# Singleton instance
_repo_validator: Optional[RepoValidator] = None


def get_repo_validator() -> RepoValidator:
    """Get or create RepoValidator instance"""
    global _repo_validator
    if _repo_validator is None:
        _repo_validator = RepoValidator()
    return _repo_validator
