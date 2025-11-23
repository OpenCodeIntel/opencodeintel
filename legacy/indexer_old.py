"""
Code Indexer
Handles code parsing, embedding generation, and semantic search
"""
import os
from pathlib import Path
from typing import List, Dict, Optional
import asyncio

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

# Import cache service
from services.cache import CacheService

load_dotenv()


class CodeIndexer:
    """Index and search code using semantic embeddings"""
    
    def __init__(self):
        # Initialize cache
        self.cache = CacheService()
        
        # Initialize OpenAI
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Initialize Pinecone
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        
        index_name = os.getenv("PINECONE_INDEX_NAME", "codeintel")
        
        # Create index if it doesn't exist
        if index_name not in pc.list_indexes().names():
            print(f"Creating Pinecone index: {index_name}")
            pc.create_index(
                name=index_name,
                dimension=1536,  # OpenAI embedding dimension
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
        
        print("CodeIndexer initialized!")
    
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
        skip_dirs = {'node_modules', '.git', '__pycache__', 'venv', 'env', 'dist', 'build'}
        
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
    
    async def _create_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI with caching"""
        try:
            # Truncate if too long
            text = text[:8000]
            
            # Check cache first
            cached = self.cache.get_embedding(text)
            if cached:
                return cached
            
            # Generate new embedding
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            embedding = response.data[0].embedding
            
            # Cache it
            self.cache.set_embedding(text, embedding)
            
            return embedding
        except Exception as e:
            print(f"Error creating embedding: {e}")
            return [0.0] * 1536
    
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
        """Index all code in a repository"""
        print(f"Indexing repository: {repo_id} at {repo_path}")
        
        # Discover code files
        code_files = self._discover_code_files(repo_path)
        print(f"Found {len(code_files)} code files")
        
        # Process files in batches
        batch_size = 5
        total_functions = 0
        
        for i in range(0, len(code_files), batch_size):
            batch = code_files[i:i + batch_size]
            results = await asyncio.gather(
                *[self._index_file(repo_id, str(file_path)) for file_path in batch],
                return_exceptions=True
            )
            
            for result in results:
                if isinstance(result, int):
                    total_functions += result
            
            print(f"Processed {i + len(batch)}/{len(code_files)} files, {total_functions} functions indexed")
        
        print(f"Indexing complete! Total functions: {total_functions}")
        return total_functions
    
    async def _index_file(self, repo_id: str, file_path: str) -> int:
        """Index a single file"""
        try:
            # Detect language
            language = self._detect_language(file_path)
            if not language or language not in self.parsers:
                return 0
            
            # Read file
            with open(file_path, 'rb') as f:
                source_code = f.read()
            
            # Parse with tree-sitter
            tree = self.parsers[language].parse(source_code)
            
            # Extract functions
            functions = self._extract_functions(tree.root_node, source_code)
            
            if not functions:
                return 0
            
            # Generate embeddings and store in Pinecone
            vectors_to_upsert = []
            
            for func in functions:
                # Create text for embedding
                embedding_text = f"Function: {func['name']}\nType: {func['type']}\n\n{func['code']}"
                
                # Generate embedding
                embedding = await self._create_embedding(embedding_text)
                
                # Create unique ID
                func_id = hashlib.md5(f"{repo_id}:{file_path}:{func['start_line']}".encode()).hexdigest()
                
                # Prepare vector
                vectors_to_upsert.append({
                    "id": func_id,
                    "values": embedding,
                    "metadata": {
                        "repo_id": repo_id,
                        "file_path": file_path,
                        "name": func['name'],
                        "type": func['type'],
                        "code": func['code'][:1000],  # Limit code length in metadata
                        "start_line": func['start_line'],
                        "end_line": func['end_line'],
                        "language": language
                    }
                })
            
            # Upsert to Pinecone
            if vectors_to_upsert:
                self.index.upsert(vectors=vectors_to_upsert)
            
            return len(functions)
            
        except Exception as e:
            print(f"Error indexing file {file_path}: {e}")
            return 0
    
    async def semantic_search(
        self,
        query: str,
        repo_id: str,
        max_results: int = 10
    ) -> List[Dict]:
        """Search code using semantic similarity with caching"""
        try:
            # Check cache first
            cached_results = self.cache.get_search_results(query, repo_id)
            if cached_results:
                print(f"✅ Cache HIT for query: {query[:50]}")
                return cached_results
            
            print(f"❌ Cache MISS for query: {query[:50]}")
            
            # Generate query embedding (this will use embedding cache)
            query_embedding = await self._create_embedding(query)
            
            # Search Pinecone
            results = self.index.query(
                vector=query_embedding,
                filter={"repo_id": {"$eq": repo_id}},
                top_k=max_results,
                include_metadata=True
            )
            
            # Format results
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
            
            # Cache results
            self.cache.set_search_results(query, repo_id, formatted_results)
            
            return formatted_results
            
        except Exception as e:

            print(f"Error searching: {e}")
            return []
    
    async def explain_code(
        self,
        repo_id: str,
        file_path: str,
        function_name: Optional[str] = None
    ) -> str:
        """Generate natural language explanation of code using Claude"""
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
            
            # Use OpenAI to explain (we could use Claude API too)
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Cheaper and faster
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful code explainer. Explain code clearly and concisely, focusing on what it does, how it works, and any important patterns or techniques used."
                    },
                    {
                        "role": "user",
                        "content": f"Explain this code:\n\n```\n{code_content}\n```"
                    }
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            explanation = response.choices[0].message.content
            return explanation
            
        except Exception as e:
            print(f"Error explaining code: {e}")
            return f"Error generating explanation: {str(e)}"
