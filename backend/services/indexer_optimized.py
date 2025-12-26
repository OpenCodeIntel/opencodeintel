"""
Optimized Code Indexer
High-performance indexing with batch embeddings and parallel processing

Improvements (v2):
- Uses text-embedding-3-large for better code understanding
- Rich embedding text with docstrings, params, and context
- Query expansion for better recall
- Keyword boosting for exact matches
"""
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import asyncio
from collections import defaultdict

# Tree-sitter for parsing
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Parser

# AI/ML
from openai import AsyncOpenAI
from pinecone import Pinecone, ServerlessSpec

# Utils
import hashlib
from dotenv import load_dotenv
import time

# Search enhancement
from services.search_enhancer import SearchEnhancer

# Observability
from services.observability import logger, trace_operation, track_time, capture_exception, add_breadcrumb, metrics

load_dotenv()

# Configuration
# Note: If using existing Pinecone index, match the dimension (1536 for small, 3072 for large)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = 3072 if "large" in EMBEDDING_MODEL else 1536


class OptimizedCodeIndexer:
    """Index and search code using semantic embeddings - OPTIMIZED"""
    
    # Batch sizes for optimal performance
    EMBEDDING_BATCH_SIZE = 100  # OpenAI allows up to 2048
    FILE_BATCH_SIZE = 10  # Process files in parallel
    PINECONE_UPSERT_BATCH = 100  # Pinecone batch upsert
    
    def __init__(self):
        # Initialize OpenAI
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Initialize search enhancer
        self.search_enhancer = SearchEnhancer(self.openai_client)
        
        # Initialize Pinecone
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        
        index_name = os.getenv("PINECONE_INDEX_NAME", "codeintel")
        
        # Check if index exists and has correct dimensions
        existing_indexes = pc.list_indexes().names()
        if index_name in existing_indexes:
            # Use existing index (dimension already set)
            index_info = pc.describe_index(index_name)
            logger.info("Using existing Pinecone index", index=index_name, dimension=index_info.dimension)
        else:
            logger.info("Creating Pinecone index", index=index_name, dimension=EMBEDDING_DIMENSIONS)
            pc.create_index(
                name=index_name,
                dimension=EMBEDDING_DIMENSIONS,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
        
        self.index = pc.Index(index_name)
        
        # Initialize tree-sitter parsers
        self.parsers = {
            'python': self._create_parser(Language(tspython.language())),
            'javascript': self._create_parser(Language(tsjavascript.language())),
            'typescript': self._create_parser(Language(tsjavascript.language())),
        }
        
        logger.info("OptimizedCodeIndexer initialized", model=EMBEDDING_MODEL)
    
    def _create_parser(self, language) -> Parser:
        """Create a tree-sitter parser"""
        parser = Parser(language)
        return parser
    
    def _detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension"""
        ext = Path(file_path).suffix.lower()
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
        }
        return lang_map.get(ext)
    
    def _discover_code_files(self, repo_path: str) -> List[Path]:
        """Find all code files in repository"""
        repo_path = Path(repo_path)
        code_files = []
        
        # Extensions to index
        extensions = {'.py', '.js', '.jsx', '.ts', '.tsx'}
        
        # Directories to skip
        skip_dirs = {'node_modules', '.git', '__pycache__', 'venv', 'env', 'dist', 'build', '.next', '.vscode'}
        
        for file_path in repo_path.rglob('*'):
            # Skip directories
            if file_path.is_dir():
                continue
            
            # Skip if in excluded directory
            if any(skip in file_path.parts for skip in skip_dirs):
                continue
            
            # Check extension
            if file_path.suffix in extensions:
                code_files.append(file_path)
        
        return code_files
    
    async def _create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in batch using configured model"""
        if not texts:
            return []
        
        try:
            # Truncate texts if too long (8191 token limit)
            truncated_texts = [text[:8000] for text in texts]
            
            response = await self.openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=truncated_texts
            )
            
            # Return embeddings in order
            return [item.embedding for item in response.data]
            
        except Exception as e:
            logger.error("Error creating batch embeddings", error=str(e), batch_size=len(texts))
            capture_exception(e, operation="create_embeddings", batch_size=len(texts))
            # Return zero vectors on error
            return [[0.0] * EMBEDDING_DIMENSIONS for _ in texts]
    
    def _extract_functions(self, tree_node, source_code: bytes) -> List[Dict]:
        """Extract function/class definitions from AST"""
        functions = []
        
        # Function/class node types
        target_types = {
            'function_definition',
            'class_definition',
            'function_declaration',
            'method_definition',
            'arrow_function',
        }
        
        if tree_node.type in target_types:
            # Extract function name
            name_node = None
            for child in tree_node.children:
                if child.type == 'identifier':
                    name_node = child
                    break
            
            name = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8') if name_node else 'anonymous'
            
            code = source_code[tree_node.start_byte:tree_node.end_byte].decode('utf-8')
            
            functions.append({
                'name': name,
                'type': tree_node.type,
                'code': code,
                'start_line': tree_node.start_point[0],
                'end_line': tree_node.end_point[0],
            })
        
        # Recursively search children
        for child in tree_node.children:
            functions.extend(self._extract_functions(child, source_code))
        
        return functions
    
    async def index_repository(self, repo_id: str, repo_path: str):
        """Index all code in a repository - OPTIMIZED VERSION"""
        from services.observability import set_operation_context
        
        set_operation_context("indexing", repo_id=repo_id)
        add_breadcrumb("Starting repository indexing", category="indexing", repo_id=repo_id)
        
        start_time = time.time()
        logger.info("Starting optimized indexing", repo_id=repo_id, path=repo_path)
        
        # Discover code files
        code_files = self._discover_code_files(repo_path)
        logger.info("Code files discovered", repo_id=repo_id, file_count=len(code_files))
        
        if not code_files:
            logger.warning("No code files found", repo_id=repo_id)
            return 0
        
        # Extract all functions from all files (parallel)
        all_functions_data = []
        
        add_breadcrumb("Extracting functions", category="indexing", file_count=len(code_files))
        for i in range(0, len(code_files), self.FILE_BATCH_SIZE):
            batch = code_files[i:i + self.FILE_BATCH_SIZE]
            
            # Extract functions in parallel
            batch_results = await asyncio.gather(
                *[self._extract_functions_from_file(repo_id, str(file_path)) 
                  for file_path in batch],
                return_exceptions=True
            )
            
            # Collect valid results
            for result in batch_results:
                if isinstance(result, list):
                    all_functions_data.extend(result)
            
            processed = min(i + self.FILE_BATCH_SIZE, len(code_files))
            logger.debug("File batch processed", processed=processed, total=len(code_files), functions=len(all_functions_data))
        
        if not all_functions_data:
            logger.warning("No functions extracted", repo_id=repo_id)
            return 0
        
        logger.info("Functions extracted", repo_id=repo_id, count=len(all_functions_data))
        add_breadcrumb("Functions extracted", category="indexing", count=len(all_functions_data))
        
        # Generate embeddings in BATCHES (this is the key optimization)
        logger.info("Generating embeddings", batch_size=self.EMBEDDING_BATCH_SIZE, model=EMBEDDING_MODEL)
        
        # Create rich embedding texts using search enhancer
        embedding_texts = [
            self.search_enhancer.create_rich_embedding_text(func)
            for func in all_functions_data
        ]
        
        all_embeddings = []
        with track_time("embedding_generation", repo_id=repo_id, total=len(embedding_texts)):
            for i in range(0, len(embedding_texts), self.EMBEDDING_BATCH_SIZE):
                batch_texts = embedding_texts[i:i + self.EMBEDDING_BATCH_SIZE]
                batch_embeddings = await self._create_embeddings_batch(batch_texts)
                all_embeddings.extend(batch_embeddings)
                
                logger.debug("Embeddings generated", progress=len(all_embeddings), total=len(embedding_texts))
        
        # Prepare vectors for Pinecone
        add_breadcrumb("Uploading to Pinecone", category="indexing", vector_count=len(all_functions_data))
        vectors_to_upsert = []
        
        for func_data, embedding in zip(all_functions_data, all_embeddings):
            func_id = hashlib.md5(
                f"{repo_id}:{func_data['file_path']}:{func_data['start_line']}".encode()
            ).hexdigest()
            
            vectors_to_upsert.append({
                "id": func_id,
                "values": embedding,
                "metadata": {
                    "repo_id": repo_id,
                    "file_path": func_data['file_path'],
                    "name": func_data['name'],
                    "type": func_data['type'],
                    "code": func_data['code'][:1000],
                    "start_line": func_data['start_line'],
                    "end_line": func_data['end_line'],
                    "language": func_data['language']
                }
            })
        
        # Upsert to Pinecone in batches
        with track_time("pinecone_upload", repo_id=repo_id, vectors=len(vectors_to_upsert)):
            for i in range(0, len(vectors_to_upsert), self.PINECONE_UPSERT_BATCH):
                batch = vectors_to_upsert[i:i + self.PINECONE_UPSERT_BATCH]
                self.index.upsert(vectors=batch)
                logger.debug("Vectors uploaded", progress=min(i + self.PINECONE_UPSERT_BATCH, len(vectors_to_upsert)), total=len(vectors_to_upsert))
        
        elapsed = time.time() - start_time
        speed = len(all_functions_data) / elapsed if elapsed > 0 else 0
        
        logger.info(
            "Indexing complete",
            repo_id=repo_id,
            functions=len(all_functions_data),
            duration_s=round(elapsed, 2),
            speed=round(speed, 1)
        )
        metrics.increment("indexing_completed")
        metrics.timing("indexing_duration_s", elapsed)
        
        return len(all_functions_data)
    
    async def _extract_functions_from_file(
        self, 
        repo_id: str, 
        file_path: str
    ) -> List[Dict]:
        """Extract functions from a single file and return with metadata"""
        try:
            # Detect language
            language = self._detect_language(file_path)
            if not language or language not in self.parsers:
                return []
            
            # Read file
            with open(file_path, 'rb') as f:
                source_code = f.read()
            
            # Parse with tree-sitter
            tree = self.parsers[language].parse(source_code)
            
            # Extract functions
            functions = self._extract_functions(tree.root_node, source_code)
            
            # Add metadata to each function
            for func in functions:
                func['file_path'] = file_path
                func['language'] = language
            
            return functions
            
        except Exception as e:
            logger.error("Error processing file", file_path=file_path, error=str(e))
            return []
    
    async def semantic_search(
        self,
        query: str,
        repo_id: str,
        max_results: int = 10,
        use_query_expansion: bool = True,
        use_reranking: bool = True
    ) -> List[Dict]:
        """
        Search code using semantic similarity with enhancements.
        
        Args:
            query: Search query
            repo_id: Repository to search in
            max_results: Number of results to return
            use_query_expansion: Expand query with related terms
            use_reranking: Rerank results with keyword boosting
        """
        start_time = time.time()
        metrics.increment("search_requests")
        
        try:
            # Step 1: Query expansion (adds related programming terms)
            search_query = query
            if use_query_expansion:
                search_query = await self.search_enhancer.expand_query(query)
                logger.debug("Query expanded", original=query[:50], expanded=search_query[:100])
            
            # Step 2: Generate query embedding
            query_embeddings = await self._create_embeddings_batch([search_query])
            query_embedding = query_embeddings[0]
            
            # Step 3: Search Pinecone (retrieve more for reranking)
            retrieve_count = max_results * 3 if use_reranking else max_results
            results = self.index.query(
                vector=query_embedding,
                filter={"repo_id": {"$eq": repo_id}},
                top_k=retrieve_count,
                include_metadata=True
            )
            
            # Step 4: Format results
            formatted_results = []
            for match in results.matches:
                formatted_results.append({
                    "code": match.metadata.get("code", ""),
                    "file_path": match.metadata.get("file_path", ""),
                    "name": match.metadata.get("name", ""),
                    "type": match.metadata.get("type", ""),
                    "language": match.metadata.get("language", ""),
                    "score": float(match.score),
                    "line_start": match.metadata.get("start_line", 0),
                    "line_end": match.metadata.get("end_line", 0),
                })
            
            # Step 5: Rerank with keyword boosting
            if use_reranking and formatted_results:
                formatted_results = self.search_enhancer.rerank_results(
                    query,  # Use original query for keyword matching
                    formatted_results
                )
            
            elapsed = time.time() - start_time
            logger.info("Search completed", repo_id=repo_id, results=len(formatted_results), duration_ms=round(elapsed*1000, 2))
            metrics.timing("search_latency_ms", elapsed * 1000)
            
            return formatted_results[:max_results]
            
        except Exception as e:
            capture_exception(e, operation="search", repo_id=repo_id, query=query[:100])
            logger.error("Search failed", repo_id=repo_id, error=str(e))
            metrics.increment("search_errors")
            return []
    
    async def explain_code(
        self,
        repo_id: str,
        file_path: str,
        function_name: Optional[str] = None
    ) -> str:
        """Generate natural language explanation of code"""
        try:
            # Read the file
            with open(file_path, 'r') as f:
                code_content = f.read()
            
            # If function_name provided, try to find it
            if function_name:
                language = self._detect_language(file_path)
                if language and language in self.parsers:
                    tree = self.parsers[language].parse(code_content.encode('utf-8'))
                    functions = self._extract_functions(tree.root_node, code_content.encode('utf-8'))
                    
                    # Find matching function
                    for func in functions:
                        if func['name'] == function_name:
                            code_content = func['code']
                            break
            
            # Use OpenAI to explain
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful code explainer. Explain code clearly and concisely."
                    },
                    {
                        "role": "user",
                        "content": f"Explain this code:\n\n```\n{code_content[:2000]}\n```"
                    }
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error("Error explaining code", file_path=file_path, error=str(e))
            capture_exception(e, operation="explain_code", file_path=file_path)
            return f"Error: {str(e)}"

    async def index_repository_with_progress(
        self,
        repo_id: str,
        repo_path: str,
        progress_callback,
        max_files: int = None
    ):
        """Index repository with real-time progress updates

        Args:
            max_files: If set, limit indexing to first N files (for partial indexing)
        """
        start_time = time.time()
        logger.info("Starting optimized indexing with progress", repo_id=repo_id)

        # Discover code files
        code_files = self._discover_code_files(repo_path)

        # Apply file limit if specified (partial indexing)
        if max_files and len(code_files) > max_files:
            logger.info("Limiting files for partial indexing",
                        total_discovered=len(code_files),
                        max_files=max_files)
            code_files = code_files[:max_files]

        total_files = len(code_files)
        logger.info("Found code files", repo_id=repo_id, total_files=total_files)
        
        if not code_files:
            await progress_callback(0, 0, 0)
            return 0
        
        # Extract all functions from all files
        all_functions_data = []
        files_processed = 0
        
        logger.debug("Extracting functions from files")
        for i in range(0, len(code_files), self.FILE_BATCH_SIZE):
            batch = code_files[i:i + self.FILE_BATCH_SIZE]
            
            # Extract functions in parallel
            batch_results = await asyncio.gather(
                *[self._extract_functions_from_file(repo_id, str(file_path)) 
                  for file_path in batch],
                return_exceptions=True
            )
            
            # Collect valid results
            for result in batch_results:
                if isinstance(result, list):
                    all_functions_data.extend(result)
            
            files_processed = min(i + self.FILE_BATCH_SIZE, total_files)
            
            # Send progress update
            await progress_callback(files_processed, len(all_functions_data), total_files)
            
            logger.debug("Processing files", 
                        processed=files_processed, 
                        total=total_files, 
                        functions_extracted=len(all_functions_data))
        
        if not all_functions_data:
            return 0
        
        # Generate embeddings in BATCHES
        logger.debug("Generating embeddings in batches", batch_size=self.EMBEDDING_BATCH_SIZE)
        
        # Create rich embedding texts using search enhancer
        embedding_texts = [
            self.search_enhancer.create_rich_embedding_text(func)
            for func in all_functions_data
        ]
        
        all_embeddings = []
        for i in range(0, len(embedding_texts), self.EMBEDDING_BATCH_SIZE):
            batch_texts = embedding_texts[i:i + self.EMBEDDING_BATCH_SIZE]
            batch_embeddings = await self._create_embeddings_batch(batch_texts)
            all_embeddings.extend(batch_embeddings)
            
            logger.debug("Embeddings generated", completed=len(all_embeddings), total=len(embedding_texts))
        
        # Prepare vectors for Pinecone
        logger.debug("Uploading to Pinecone")
        vectors_to_upsert = []
        
        for func_data, embedding in zip(all_functions_data, all_embeddings):
            func_id = hashlib.md5(
                f"{repo_id}:{func_data['file_path']}:{func_data['start_line']}".encode()
            ).hexdigest()
            
            vectors_to_upsert.append({
                "id": func_id,
                "values": embedding,
                "metadata": {
                    "repo_id": repo_id,
                    "file_path": func_data['file_path'],
                    "name": func_data['name'],
                    "type": func_data['type'],
                    "code": func_data['code'][:1000],
                    "start_line": func_data['start_line'],
                    "end_line": func_data['end_line'],
                    "language": func_data['language']
                }
            })
        
        # Upsert to Pinecone in batches
        for i in range(0, len(vectors_to_upsert), self.PINECONE_UPSERT_BATCH):
            batch = vectors_to_upsert[i:i + self.PINECONE_UPSERT_BATCH]
            self.index.upsert(vectors=batch)
        
        elapsed = time.time() - start_time
        logger.info("Indexing with progress complete",
                    repo_id=repo_id,
                    total_functions=len(all_functions_data),
                    duration_s=round(elapsed, 2),
                    speed=round(len(all_functions_data)/elapsed, 1) if elapsed > 0 else 0)
        
        return len(all_functions_data)

    async def incremental_index_repository(
        self, 
        repo_id: str, 
        repo_path: str,
        last_commit_sha: str
    ):
        """Incrementally index only changed files since last commit"""
        import git
        import time
        
        start_time = time.time()
        logger.info("Starting INCREMENTAL indexing", repo_id=repo_id, last_commit=last_commit_sha[:8])
        
        try:
            repo = git.Repo(repo_path)
            current_commit = repo.head.commit.hexsha
            
            logger.debug("Current commit", current_commit=current_commit[:8])
            
            # Get changed files
            if last_commit_sha:
                diff = repo.git.diff(last_commit_sha, current_commit, '--name-only')
                changed_files = diff.split('\n') if diff else []
            else:
                # No previous commit, index everything
                logger.warning("No previous commit - doing full index")
                return await self.index_repository(repo_id, repo_path)
            
            # Filter for code files only
            code_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx'}
            changed_code_files = [
                f for f in changed_files 
                if Path(f).suffix in code_extensions
            ]
            
            logger.info("Found changed files", total_changes=len(changed_files), code_files=len(changed_code_files))
            
            if not changed_code_files:
                logger.info("No code changes detected - skipping indexing")
                return 0
            
            # Extract functions from changed files
            all_functions_data = []
            
            for file_path in changed_code_files:
                full_path = Path(repo_path) / file_path
                if not full_path.exists():
                    logger.debug("File deleted - skipping", file_path=file_path)
                    continue
                
                functions = await self._extract_functions_from_file(repo_id, str(full_path))
                all_functions_data.extend(functions)
                logger.debug("Processed changed file", file_path=file_path, functions=len(functions))
            
            if not all_functions_data:
                logger.info("No functions to index")
                return 0
            
            # Generate embeddings in batches
            logger.debug("Generating embeddings", function_count=len(all_functions_data))
            
            # Create rich embedding texts using search enhancer
            embedding_texts = [
                self.search_enhancer.create_rich_embedding_text(func)
                for func in all_functions_data
            ]
            
            all_embeddings = []
            for i in range(0, len(embedding_texts), self.EMBEDDING_BATCH_SIZE):
                batch_texts = embedding_texts[i:i + self.EMBEDDING_BATCH_SIZE]
                batch_embeddings = await self._create_embeddings_batch(batch_texts)
                all_embeddings.extend(batch_embeddings)
            
            # Prepare vectors
            vectors_to_upsert = []
            
            for func_data, embedding in zip(all_functions_data, all_embeddings):
                func_id = hashlib.md5(
                    f"{repo_id}:{func_data['file_path']}:{func_data['start_line']}".encode()
                ).hexdigest()
                
                vectors_to_upsert.append({
                    "id": func_id,
                    "values": embedding,
                    "metadata": {
                        "repo_id": repo_id,
                        "file_path": func_data['file_path'],
                        "name": func_data['name'],
                        "type": func_data['type'],
                        "code": func_data['code'][:1000],
                        "start_line": func_data['start_line'],
                        "end_line": func_data['end_line'],
                        "language": func_data['language']
                    }
                })
            
            # Upsert to Pinecone
            for i in range(0, len(vectors_to_upsert), self.PINECONE_UPSERT_BATCH):
                batch = vectors_to_upsert[i:i + self.PINECONE_UPSERT_BATCH]
                self.index.upsert(vectors=batch)
            
            elapsed = time.time() - start_time
            
            logger.info("Incremental indexing complete",
                        repo_id=repo_id,
                        changed_files=len(changed_code_files),
                        functions_updated=len(all_functions_data),
                        duration_s=round(elapsed, 2),
                        speed=round(len(all_functions_data)/elapsed, 1) if elapsed > 0 else 0)
            
            return len(all_functions_data)
            
        except Exception as e:
            logger.error("Incremental indexing error - falling back to full index", 
                        repo_id=repo_id, error=str(e))
            capture_exception(e, operation="incremental_indexing", repo_id=repo_id)
            return await self.index_repository(repo_id, repo_path)
