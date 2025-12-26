"""
Anonymous Indexing Service (#125)

Handles job management and background indexing for anonymous users.
Jobs are tracked in Redis with progress updates.
"""
import uuid
import json
import shutil
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional
from dataclasses import dataclass, asdict
from enum import Enum

import git

from services.observability import logger, metrics, capture_exception


class JobStatus(str, Enum):
    """Job status values."""
    QUEUED = "queued"
    CLONING = "cloning"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class JobProgress:
    """Progress tracking for indexing job."""
    files_total: int = 0
    files_processed: int = 0
    functions_found: int = 0
    current_file: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class JobStats:
    """Final stats for completed job."""
    files_indexed: int = 0
    functions_found: int = 0
    time_taken_seconds: float = 0

    def to_dict(self) -> dict:
        return asdict(self)


class AnonymousIndexingJob:
    """
    Manages anonymous indexing jobs in Redis.

    Redis key: anon_job:{job_id}
    TTL: 1 hour for job metadata
    """

    REDIS_PREFIX = "anon_job:"
    JOB_TTL_SECONDS = 3600  # 1 hour for job metadata
    REPO_TTL_HOURS = 24  # 24 hours for indexed data
    TEMP_DIR = "/tmp/anon_repos"
    CLONE_TIMEOUT_SECONDS = 120  # 2 minutes for clone
    INDEX_TIMEOUT_SECONDS = 300  # 5 minutes for indexing

    def __init__(self, redis_client):
        self.redis = redis_client
        # Ensure temp directory exists
        Path(self.TEMP_DIR).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def generate_job_id() -> str:
        """Generate unique job ID."""
        return f"idx_{uuid.uuid4().hex[:12]}"

    @staticmethod
    def generate_repo_id(job_id: str) -> str:
        """Generate repo ID from job ID (for Pinecone namespace)."""
        return f"anon_{job_id.replace('idx_', '')}"

    def _get_key(self, job_id: str) -> str:
        """Get Redis key for job."""
        return f"{self.REDIS_PREFIX}{job_id}"

    def create_job(
        self,
        job_id: str,
        session_id: str,
        github_url: str,
        owner: str,
        repo_name: str,
        branch: str,
        file_count: int,
        is_partial: bool = False,
        max_files: Optional[int] = None
    ) -> dict:
        """
        Create a new indexing job in Redis.

        Returns the initial job state.
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=self.REPO_TTL_HOURS)

        job_data = {
            "job_id": job_id,
            "session_id": session_id,
            "github_url": github_url,
            "owner": owner,
            "repo_name": repo_name,
            "branch": branch,
            "file_count": file_count,
            "is_partial": is_partial,
            "max_files": max_files,
            "status": JobStatus.QUEUED.value,
            "progress": None,
            "stats": None,
            "repo_id": None,
            "error": None,
            "error_message": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
        }

        if self.redis:
            key = self._get_key(job_id)
            self.redis.setex(key, self.JOB_TTL_SECONDS, json.dumps(job_data))
            logger.info("Created indexing job", job_id=job_id, session_id=session_id[:8])

        return job_data

    def get_job(self, job_id: str) -> Optional[dict]:
        """Get job data from Redis."""
        if not self.redis:
            return None

        key = self._get_key(job_id)
        data = self.redis.get(key)

        if not data:
            return None

        try:
            return json.loads(data)
        except json.JSONDecodeError:
            logger.error("Invalid job data in Redis", job_id=job_id)
            return None

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        progress: Optional[JobProgress] = None,
        stats: Optional[JobStats] = None,
        repo_id: Optional[str] = None,
        error: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update job status in Redis."""
        if not self.redis:
            return False

        job = self.get_job(job_id)
        if not job:
            logger.warning("Job not found for update", job_id=job_id)
            return False

        job["status"] = status.value
        job["updated_at"] = datetime.now(timezone.utc).isoformat()

        if progress:
            job["progress"] = progress.to_dict()
        if stats:
            job["stats"] = stats.to_dict()
        if repo_id:
            job["repo_id"] = repo_id
        if error:
            job["error"] = error
            job["error_message"] = error_message

        key = self._get_key(job_id)
        self.redis.setex(key, self.JOB_TTL_SECONDS, json.dumps(job))

        return True

    def update_progress(
        self,
        job_id: str,
        files_processed: int,
        functions_found: int,
        files_total: int,
        current_file: Optional[str] = None
    ) -> bool:
        """Update job progress (called during indexing)."""
        progress = JobProgress(
            files_total=files_total,
            files_processed=files_processed,
            functions_found=functions_found,
            current_file=current_file
        )
        return self.update_status(job_id, JobStatus.PROCESSING, progress=progress)

    def get_temp_path(self, job_id: str) -> Path:
        """Get temp directory path for job."""
        return Path(self.TEMP_DIR) / job_id

    def cleanup_temp(self, job_id: str) -> None:
        """Clean up temp directory for job."""
        temp_path = self.get_temp_path(job_id)
        if temp_path.exists():
            try:
                shutil.rmtree(temp_path)
                logger.debug("Cleaned up temp directory", job_id=job_id)
            except Exception as e:
                logger.warning("Failed to cleanup temp", job_id=job_id, error=str(e))


async def run_indexing_job(
    job_manager: AnonymousIndexingJob,
    indexer,
    limiter,
    job_id: str,
    session_id: str,
    github_url: str,
    owner: str,
    repo_name: str,
    branch: str,
    file_count: int,
    max_files: Optional[int] = None
) -> None:
    """
    Background task to clone and index a repository.

    This runs asynchronously after the endpoint returns.
    Updates Redis with progress and final status.

    Args:
        max_files: If set, limit indexing to first N files (for partial indexing)
    """
    import time
    start_time = time.time()
    temp_path = job_manager.get_temp_path(job_id)
    repo_id = job_manager.generate_repo_id(job_id)

    try:
        # --- Step 1: Clone repository ---
        job_manager.update_status(job_id, JobStatus.CLONING)
        logger.info("Cloning repository", job_id=job_id, url=github_url)

        git_url = f"https://github.com/{owner}/{repo_name}.git"

        # Clone in thread pool (git operations are blocking)
        loop = asyncio.get_event_loop()
        try:
            await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: git.Repo.clone_from(
                        git_url,
                        temp_path,
                        branch=branch,
                        depth=1,  # Shallow clone
                        single_branch=True
                    )
                ),
                timeout=job_manager.CLONE_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            raise Exception("Clone timed out")
        except git.GitCommandError as e:
            raise Exception(f"Clone failed: {str(e)}")

        logger.info("Clone complete", job_id=job_id)

        # --- Step 2: Index repository ---
        job_manager.update_status(job_id, JobStatus.PROCESSING)

        # Progress callback for real-time updates
        async def progress_callback(files_processed: int, functions_found: int, total: int):
            job_manager.update_progress(
                job_id,
                files_processed=files_processed,
                functions_found=functions_found,
                files_total=total
            )

        # Run indexing with timeout
        try:
            total_functions = await asyncio.wait_for(
                indexer.index_repository_with_progress(
                    repo_id,
                    str(temp_path),
                    progress_callback,
                    max_files=max_files
                ),
                timeout=job_manager.INDEX_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            raise Exception("Indexing timed out")

        # --- Step 3: Mark complete ---
        elapsed = time.time() - start_time
        stats = JobStats(
            files_indexed=file_count,
            functions_found=total_functions,
            time_taken_seconds=round(elapsed, 2)
        )

        job_manager.update_status(
            job_id,
            JobStatus.COMPLETED,
            stats=stats,
            repo_id=repo_id
        )

        # Store in session for search access
        job = job_manager.get_job(job_id)
        if job and limiter:
            limiter.set_indexed_repo(session_id, {
                "repo_id": repo_id,
                "github_url": github_url,
                "name": repo_name,
                "file_count": file_count,
                "indexed_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": job.get("expires_at"),
            })

        metrics.increment("anon_indexing_success")
        logger.info("Indexing complete",
                    job_id=job_id,
                    repo_id=repo_id,
                    functions=total_functions,
                    elapsed=f"{elapsed:.2f}s")

    except Exception as e:
        # --- Handle failure ---
        error_msg = str(e)
        error_type = "indexing_failed"

        if "timed out" in error_msg.lower():
            error_type = "timeout"
        elif "clone" in error_msg.lower():
            error_type = "clone_failed"
        elif "rate limit" in error_msg.lower():
            error_type = "github_rate_limit"

        job_manager.update_status(
            job_id,
            JobStatus.FAILED,
            error=error_type,
            error_message=error_msg
        )

        metrics.increment("anon_indexing_failed")
        logger.error("Indexing failed",
                     job_id=job_id,
                     error_type=error_type,
                     error=error_msg)
        capture_exception(e, operation="anonymous_indexing", job_id=job_id)

    finally:
        # --- Always cleanup ---
        job_manager.cleanup_temp(job_id)
