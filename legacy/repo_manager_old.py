"""
Repository Manager
Handles repository CRUD operations (in-memory for MVP, later DB)
"""
import uuid
from typing import Dict, List, Optional
import os
import git
from pathlib import Path


class RepositoryManager:
    """Manage repositories"""
    
    def __init__(self):
        # In-memory storage (Phase 1 MVP)
        # Later: replace with PostgreSQL
        self.repos: Dict[str, dict] = {}
        self.repos_dir = Path("./repos")
        self.repos_dir.mkdir(exist_ok=True)
        
        # Discover existing repositories on startup
        self._discover_existing_repos()
    
    def _discover_existing_repos(self):
        """Scan repos directory and load existing repositories"""
        if not self.repos_dir.exists():
            return
        
        for repo_path in self.repos_dir.iterdir():
            if not repo_path.is_dir() or repo_path.name.startswith('.'):
                continue
            
            try:
                # Try to open as git repo
                repo = git.Repo(repo_path)
                
                # Get repo info from git config
                remote_url = None
                if repo.remotes:
                    remote_url = repo.remotes.origin.url
                
                # Extract name from URL or use folder name
                name = remote_url.split('/')[-1].replace('.git', '') if remote_url else repo_path.name
                branch = repo.active_branch.name if not repo.head.is_detached else "main"
                
                # Count code files to estimate if indexed
                code_files = list(repo_path.rglob('*.py')) + list(repo_path.rglob('*.js')) + list(repo_path.rglob('*.ts'))
                file_count = len([f for f in code_files if '.git' not in str(f) and 'node_modules' not in str(f)])
                
                # Add to repos
                self.repos[repo_path.name] = {
                    "id": repo_path.name,
                    "name": name,
                    "git_url": remote_url or "unknown",
                    "branch": branch,
                    "local_path": str(repo_path),
                    "status": "indexed",
                    "file_count": file_count * 20,
                    "last_indexed_commit": repo.head.commit.hexsha  # Track commit!
                }
                
                print(f"✅ Discovered existing repo: {name} ({repo_path.name}) - ~{file_count} files")
                
            except Exception as e:
                print(f"⚠️  Skipping {repo_path.name}: {e}")
    
    def list_repos(self) -> List[dict]:
        """List all repositories"""
        return list(self.repos.values())
    
    def get_repo(self, repo_id: str) -> Optional[dict]:
        """Get repository by ID"""
        return self.repos.get(repo_id)
    
    def add_repo(self, name: str, git_url: str, branch: str = "main") -> dict:
        """Add a new repository"""
        repo_id = str(uuid.uuid4())
        local_path = self.repos_dir / repo_id
        
        try:
            # Clone the repository
            print(f"Cloning {git_url} to {local_path}...")
            git.Repo.clone_from(git_url, local_path, branch=branch, depth=1)
            
            repo = {
                "id": repo_id,
                "name": name,
                "git_url": git_url,
                "branch": branch,
                "local_path": str(local_path),
                "status": "cloned",
                "file_count": 0
            }
            
            self.repos[repo_id] = repo
            return repo
            
        except Exception as e:
            # Cleanup on failure
            if local_path.exists():
                import shutil
                shutil.rmtree(local_path)
            raise Exception(f"Failed to clone repository: {str(e)}")
    
    def update_status(self, repo_id: str, status: str):
        """Update repository status"""
        if repo_id in self.repos:
            self.repos[repo_id]["status"] = status
    
    def update_file_count(self, repo_id: str, count: int):
        """Update file count"""
        if repo_id in self.repos:
            self.repos[repo_id]["file_count"] = count

    def get_last_indexed_commit(self, repo_id: str) -> str:
        """Get last indexed commit SHA"""
        if repo_id in self.repos:
            return self.repos[repo_id].get("last_indexed_commit", "")
        return ""
    
    def update_last_commit(self, repo_id: str, commit_sha: str):
        """Update last indexed commit"""
        if repo_id in self.repos:
            self.repos[repo_id]["last_indexed_commit"] = commit_sha
