"""
Repository Manager (Supabase Edition)
Handles repository CRUD operations with PostgreSQL via Supabase
"""
import uuid
from typing import Dict, List, Optional
import os
import git
from pathlib import Path
from services.supabase_service import get_supabase_service


class RepositoryManager:
    """Manage repositories with Supabase persistence"""
    
    def __init__(self):
        self.repos_dir = Path("./repos")
        self.repos_dir.mkdir(exist_ok=True)
        self.db = get_supabase_service()
        
        # Discover and sync existing repositories on startup
        self._sync_existing_repos()
    
    def _sync_existing_repos(self):
        """
        Scan repos directory and sync with Supabase
        Creates DB records for any repos found on disk but not in DB
        """
        if not self.repos_dir.exists():
            return
        
        print("🔄 Syncing repositories...")
        
        for repo_path in self.repos_dir.iterdir():
            if not repo_path.is_dir() or repo_path.name.startswith('.'):
                continue
            
            try:
                # Check if already in DB
                existing = self.db.get_repository(repo_path.name)
                if existing:
                    print(f"✅ Repo exists in DB: {existing['name']}")
                    continue
                
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
                
                # Create DB record
                self.db.create_repository(
                    repo_id=repo_path.name,
                    name=name,
                    git_url=remote_url or "unknown",
                    branch=branch,
                    local_path=str(repo_path)
                )
                
                self.db.update_last_indexed(
                    repo_path.name,
                    repo.head.commit.hexsha,
                    file_count * 20  # Estimate function count
                )
                
                print(f"✅ Synced repo from disk: {name} ({repo_path.name})")
                
            except Exception as e:
                print(f"⚠️  Error syncing {repo_path.name}: {e}")
    
    def list_repos(self) -> List[dict]:
        """List all repositories from Supabase"""
        repos = self.db.list_repositories()
        return repos
    
    def get_repo(self, repo_id: str) -> Optional[dict]:
        """Get repository by ID from Supabase"""
        return self.db.get_repository(repo_id)
    
    def add_repo(self, name: str, git_url: str, branch: str = "main", user_id: Optional[str] = None, api_key_hash: Optional[str] = None) -> dict:
        """Add a new repository"""
        repo_id = str(uuid.uuid4())
        local_path = self.repos_dir / repo_id
        
        try:
            # Clone the repository
            print(f"Cloning {git_url} to {local_path}...")
            git.Repo.clone_from(git_url, local_path, branch=branch, depth=1)
            
            # Create DB record with ownership
            repo = self.db.create_repository(
                repo_id=repo_id,
                name=name,
                git_url=git_url,
                branch=branch,
                local_path=str(local_path),
                user_id=user_id,
                api_key_hash=api_key_hash
            )
            
            return repo
            
        except Exception as e:
            # Cleanup on failure
            if local_path.exists():
                import shutil
                shutil.rmtree(local_path)
            raise Exception(f"Failed to clone repository: {str(e)}")
    
    def update_status(self, repo_id: str, status: str):
        """Update repository status"""
        self.db.update_repository_status(repo_id, status)
    
    def update_file_count(self, repo_id: str, count: int):
        """Update file count"""
        self.db.update_file_count(repo_id, count)

    def get_last_indexed_commit(self, repo_id: str) -> str:
        """Get last indexed commit SHA"""
        repo = self.db.get_repository(repo_id)
        return repo.get("last_indexed_commit", "") if repo else ""
    
    def update_last_commit(self, repo_id: str, commit_sha: str, function_count: int = 0):
        """Update last indexed commit"""
        self.db.update_last_indexed(repo_id, commit_sha, function_count)
