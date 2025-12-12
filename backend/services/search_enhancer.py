"""
Search Enhancer
Improves semantic search quality through query expansion, 
rich embeddings, and hybrid search techniques.
"""
import re
from typing import List, Dict, Optional
from openai import AsyncOpenAI
import os

from services.observability import logger, capture_exception


class SearchEnhancer:
    """Enhances search quality through various techniques"""
    
    def __init__(self, openai_client: AsyncOpenAI = None):
        self.openai_client = openai_client or AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async def expand_query(self, query: str) -> str:
        """
        Expand a search query with code-relevant terms using LLM.
        
        Example:
            "authentication" -> "authentication auth login verify user token jwt session"
        """
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a code search query expander. Given a search query, 
expand it with related programming terms, function names, and concepts.

Rules:
- Add synonyms and related terms
- Include common function/variable naming patterns (camelCase, snake_case)
- Add relevant technical terms
- Keep the expansion concise (max 15 additional terms)
- Return ONLY the expanded query, no explanations

Example:
Input: "authentication"
Output: authentication auth login verify user token jwt session authenticate validate credentials sign_in signIn is_authenticated"""
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            expanded = response.choices[0].message.content.strip()
            # Combine original query with expansion
            return f"{query} {expanded}"
            
        except Exception as e:
            logger.warning("Query expansion failed", error=str(e), query=query[:50])
            capture_exception(e, operation="query_expansion", query=query[:50])
            return query
    
    def extract_docstring(self, code: str, language: str) -> str:
        """Extract docstring/comment from function code"""
        if language == 'python':
            # Python docstrings
            patterns = [
                r'"""(.*?)"""',  # Triple double quotes
                r"'''(.*?)'''",  # Triple single quotes
            ]
            for pattern in patterns:
                match = re.search(pattern, code, re.DOTALL)
                if match:
                    return match.group(1).strip()[:200]
            
            # Single line comment after def
            match = re.search(r'def\s+\w+[^:]+:\s*#\s*(.+)', code)
            if match:
                return match.group(1).strip()
                
        else:  # JavaScript/TypeScript
            # JSDoc comments
            match = re.search(r'/\*\*(.*?)\*/', code, re.DOTALL)
            if match:
                doc = match.group(1)
                # Clean up JSDoc formatting
                doc = re.sub(r'\s*\*\s*', ' ', doc)
                return doc.strip()[:200]
            
            # Single line comments
            match = re.search(r'//\s*(.+)', code)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def extract_parameters(self, code: str, language: str) -> List[str]:
        """Extract parameter names from function signature"""
        params = []
        
        if language == 'python':
            # Match def function_name(params):
            match = re.search(r'def\s+\w+\s*\(([^)]*)\)', code)
            if match:
                param_str = match.group(1)
                # Extract parameter names (handle type hints)
                for param in param_str.split(','):
                    param = param.strip()
                    if param and param != 'self' and param != 'cls':
                        # Remove type hints and defaults
                        param_name = re.split(r'[:\=]', param)[0].strip()
                        if param_name and not param_name.startswith('*'):
                            params.append(param_name)
        else:  # JavaScript/TypeScript
            # Match function signatures
            match = re.search(r'(?:function\s+\w+|(?:async\s+)?(?:const|let|var)?\s*\w+\s*=\s*(?:async\s*)?\(?|(?:async\s+)?)\s*\(([^)]*)\)', code)
            if match:
                param_str = match.group(1)
                for param in param_str.split(','):
                    param = param.strip()
                    if param:
                        # Remove type annotations
                        param_name = re.split(r'[:\=]', param)[0].strip()
                        if param_name:
                            params.append(param_name)
        
        return params[:10]  # Limit to 10 params
    
    def extract_return_type(self, code: str, language: str) -> str:
        """Extract return type annotation if present"""
        if language == 'python':
            match = re.search(r'->\s*([^:]+):', code)
            if match:
                return match.group(1).strip()
        else:  # TypeScript
            match = re.search(r'\):\s*([^{]+)\s*{', code)
            if match:
                return match.group(1).strip()
        return ""
    
    def extract_imports_used(self, code: str, language: str) -> List[str]:
        """Extract modules/functions that are called in the code"""
        calls = set()
        
        # Find function calls
        call_pattern = r'(\w+)\s*\('
        for match in re.finditer(call_pattern, code):
            call = match.group(1)
            # Filter out language keywords
            keywords = {'if', 'for', 'while', 'with', 'def', 'class', 'return', 
                       'function', 'const', 'let', 'var', 'async', 'await'}
            if call not in keywords and not call[0].isupper():  # Exclude class instantiations
                calls.add(call)
        
        return list(calls)[:15]  # Limit to 15 calls
    
    def create_rich_embedding_text(self, func_data: Dict) -> str:
        """
        Create semantically rich text for embedding.
        
        This captures:
        - Function name and type
        - File context
        - Docstring/purpose
        - Parameters
        - Return type
        - Code structure
        """
        name = func_data.get('name', 'unknown')
        func_type = func_data.get('type', 'function')
        file_path = func_data.get('file_path', '')
        language = func_data.get('language', 'python')
        code = func_data.get('code', '')
        
        # Extract semantic information
        docstring = self.extract_docstring(code, language)
        params = self.extract_parameters(code, language)
        return_type = self.extract_return_type(code, language)
        calls = self.extract_imports_used(code, language)
        
        # Get file context (last 2 parts of path)
        file_context = '/'.join(file_path.split('/')[-2:]) if file_path else ''
        
        # Build rich embedding text
        parts = [
            f"# {func_type.replace('_', ' ').title()}: {name}",
            f"# File: {file_context}",
            f"# Language: {language}",
        ]
        
        if docstring:
            parts.append(f"# Purpose: {docstring}")
        
        if params:
            parts.append(f"# Parameters: {', '.join(params)}")
        
        if return_type:
            parts.append(f"# Returns: {return_type}")
        
        if calls:
            parts.append(f"# Uses: {', '.join(calls[:10])}")
        
        # Add the code itself (truncated)
        parts.append("")
        parts.append(code[:1500])
        
        return '\n'.join(parts)
    
    def compute_keyword_score(self, query: str, code: str, name: str) -> float:
        """
        Compute a simple keyword matching score.
        This supplements semantic search with exact matches.
        """
        query_terms = set(query.lower().split())
        
        # Check name match (highest weight)
        name_lower = name.lower()
        name_score = sum(1 for term in query_terms if term in name_lower) * 0.5
        
        # Check code match
        code_lower = code.lower()
        code_score = sum(1 for term in query_terms if term in code_lower) * 0.1
        
        return min(name_score + code_score, 0.3)  # Cap at 0.3 boost
    
    def rerank_results(
        self, 
        query: str, 
        results: List[Dict],
        boost_keyword_matches: bool = True
    ) -> List[Dict]:
        """
        Rerank results by combining semantic score with keyword matching.
        """
        if not boost_keyword_matches:
            return results
        
        reranked = []
        for result in results:
            semantic_score = result.get('score', 0)
            keyword_boost = self.compute_keyword_score(
                query, 
                result.get('code', ''),
                result.get('name', '')
            )
            
            # Combine scores: 80% semantic, 20% keyword
            combined_score = (semantic_score * 0.8) + (keyword_boost * 0.2) + keyword_boost
            
            reranked.append({
                **result,
                'score': combined_score,
                'semantic_score': semantic_score,
                'keyword_boost': keyword_boost
            })
        
        # Sort by combined score
        reranked.sort(key=lambda x: x['score'], reverse=True)
        return reranked
