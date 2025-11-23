"""
Supabase Service
Handles all database operations for CodeIntel
"""
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from supabase import create_client, Client, ClientOptions
from dotenv import load_dotenv
import uuid

load_dotenv()


class SupabaseService:
    """Service for Supabase database operations"""
    
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        # Create client with options to avoid auth cleanup issues
        options = ClientOptions(
            auto_refresh_token=False,
            persist_session=False
        )
        self.client: Client = create_client(supabase_url, supabase_key, options)
        print("✅ Supabase service initialized!")
    
    # ===== REPOSITORIES =====
    
    def create_repository(
        self,
        name: str,
        git_url: str,
        branch: str = "main",
        local_path: Optional[str] = None,
        repo_id: Optional[str] = None,
        user_id: Optional[str] = None,
        api_key_hash: Optional[str] = None
    ) -> Dict:
        """Create a new repository record"""
        data = {
            "id": repo_id or str(uuid.uuid4()),
            "name": name,
            "git_url": git_url,
            "branch": branch,
            "local_path": local_path,
            "status": "cloned",
            "user_id": user_id,
            "api_key_hash": api_key_hash
        }
        
        result = self.client.table("repositories").insert(data).execute()
        return result.data[0] if result.data else {}
    
    def get_repository(self, repo_id: str) -> Optional[Dict]:
        """Get repository by ID"""
        result = self.client.table("repositories").select("*").eq("id", repo_id).execute()
        return result.data[0] if result.data else None
    
    def list_repositories(self) -> List[Dict]:
        """List all repositories"""
        result = self.client.table("repositories").select("*").order("created_at", desc=True).execute()
        return result.data or []
    
    def update_repository(self, repo_id: str, updates: Dict) -> Optional[Dict]:
        """Update repository fields"""
        result = self.client.table("repositories").update(updates).eq("id", repo_id).execute()
        return result.data[0] if result.data else None
    
    def update_repository_status(self, repo_id: str, status: str) -> None:
        """Update repository status"""
        self.client.table("repositories").update({"status": status}).eq("id", repo_id).execute()
    
    def update_file_count(self, repo_id: str, count: int) -> None:
        """Update repository file count"""
        self.client.table("repositories").update({"file_count": count}).eq("id", repo_id).execute()
    
    def update_last_indexed(self, repo_id: str, commit_sha: str, function_count: int) -> None:
        """Update last indexed commit and timestamp"""
        self.client.table("repositories").update({
            "last_indexed_commit": commit_sha,
            "last_indexed_at": datetime.utcnow().isoformat(),
            "function_count": function_count,
            "status": "indexed"
        }).eq("id", repo_id).execute()
    
    def delete_repository(self, repo_id: str) -> None:
        """Delete repository (cascades to related tables)"""
        self.client.table("repositories").delete().eq("id", repo_id).execute()
    
    # ===== FILE DEPENDENCIES =====
    
    def upsert_file_dependencies(self, repo_id: str, dependencies: List[Dict]) -> None:
        """Bulk upsert file dependencies"""
        if not dependencies:
            return
        
        # Add repo_id to each dependency
        for dep in dependencies:
            dep["repo_id"] = repo_id
        
        # Upsert with explicit conflict resolution
        result = self.client.table("file_dependencies").upsert(
            dependencies,
            on_conflict="repo_id,file_path"
        ).execute()
        print(f"💾 Upserted {len(result.data) if result.data else 0} file dependencies")
    
    def get_file_dependencies(self, repo_id: str) -> List[Dict]:
        """Get all file dependencies for a repo"""
        result = self.client.table("file_dependencies").select("*").eq("repo_id", repo_id).execute()
        print(f"🔍 Query file_dependencies for {repo_id}: found {len(result.data) if result.data else 0} rows")
        return result.data or []
    
    def get_file_impact(self, repo_id: str, file_path: str) -> Optional[Dict]:
        """Get impact analysis for a specific file"""
        result = self.client.table("file_dependencies").select("*").eq("repo_id", repo_id).eq("file_path", file_path).execute()
        return result.data[0] if result.data else None
    
    def clear_file_dependencies(self, repo_id: str) -> None:
        """Clear all file dependencies for a repo (for reindexing)"""
        self.client.table("file_dependencies").delete().eq("repo_id", repo_id).execute()
    
    # ===== CODE STYLE ANALYSIS =====
    
    def upsert_code_style(self, repo_id: str, language: str, analysis: Dict) -> None:
        """Store code style analysis results"""
        data = {
            "repo_id": repo_id,
            "language": language,
            "naming_convention": analysis.get("naming_convention"),
            "async_usage": analysis.get("async_usage"),
            "type_hints": analysis.get("type_hints"),
            "common_imports": analysis.get("common_imports"),
            "patterns": analysis.get("patterns")
        }
        
        # Try update first, if no rows affected then insert
        result = self.client.table("code_style_analysis").update(data).eq("repo_id", repo_id).eq("language", language).execute()
        if not result.data:
            self.client.table("code_style_analysis").insert(data).execute()
    
    def get_code_style(self, repo_id: str) -> List[Dict]:
        """Get code style analysis for a repo"""
        result = self.client.table("code_style_analysis").select("*").eq("repo_id", repo_id).execute()
        return result.data or []
    
    # ===== REPOSITORY INSIGHTS =====
    
    def upsert_repository_insights(self, repo_id: str, insights: Dict) -> None:
        """Store repository insights"""
        data = {
            "repo_id": repo_id,
            "total_files": insights.get("total_files", 0),
            "total_dependencies": insights.get("total_dependencies", 0),
            "avg_dependencies_per_file": insights.get("avg_dependencies_per_file", 0),
            "max_dependencies": insights.get("max_dependencies", 0),
            "critical_files": insights.get("critical_files", []),
            "architecture_patterns": insights.get("architecture_patterns")
        }
        
        # Try update first, if no rows affected then insert
        result = self.client.table("repository_insights").update(data).eq("repo_id", repo_id).execute()
        if not result.data:
            self.client.table("repository_insights").insert(data).execute()
    
    def get_repository_insights(self, repo_id: str) -> Optional[Dict]:
        """Get repository insights"""
        result = self.client.table("repository_insights").select("*").eq("repo_id", repo_id).execute()
        return result.data[0] if result.data else None
    
    # ===== INDEXING JOBS =====
    
    def create_indexing_job(self, repo_id: str, total_files: int) -> str:
        """Create a new indexing job"""
        data = {
            "repo_id": repo_id,
            "status": "pending",
            "total_files": total_files,
            "started_at": datetime.utcnow().isoformat()
        }
        
        result = self.client.table("indexing_jobs").insert(data).execute()
        return result.data[0]["id"] if result.data else None
    
    def update_indexing_job(
        self, 
        job_id: str, 
        files_processed: int, 
        functions_indexed: int,
        status: Optional[str] = None
    ) -> None:
        """Update indexing job progress"""
        updates = {
            "files_processed": files_processed,
            "functions_indexed": functions_indexed
        }
        
        if status:
            updates["status"] = status
            if status in ["completed", "failed"]:
                updates["completed_at"] = datetime.utcnow().isoformat()
        
        self.client.table("indexing_jobs").update(updates).eq("id", job_id).execute()
    
    def fail_indexing_job(self, job_id: str, error_message: str) -> None:
        """Mark indexing job as failed"""
        self.client.table("indexing_jobs").update({
            "status": "failed",
            "error_message": error_message,
            "completed_at": datetime.utcnow().isoformat()
        }).eq("id", job_id).execute()
    
    def get_indexing_jobs(self, repo_id: str, limit: int = 10) -> List[Dict]:
        """Get recent indexing jobs for a repo"""
        result = (
            self.client.table("indexing_jobs")
            .select("*")
            .eq("repo_id", repo_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []


# Create singleton instance
_supabase_service = None

def get_supabase_service() -> SupabaseService:
    """Get or create Supabase service instance"""
    global _supabase_service
    if _supabase_service is None:
        _supabase_service = SupabaseService()
    return _supabase_service
