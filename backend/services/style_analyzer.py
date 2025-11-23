"""
Code Style Analyzer
Analyzes team coding patterns, naming conventions, and best practices
"""
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict, Counter
import re

# Tree-sitter
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Parser


class StyleAnalyzer:
    """Analyze code style and team patterns"""
    
    def __init__(self):
        # Initialize parsers
        self.parsers = {
            'python': Parser(Language(tspython.language())),
            'javascript': Parser(Language(tsjavascript.language())),
            'typescript': Parser(Language(tsjavascript.language())),
        }
        print("✅ StyleAnalyzer initialized!")
    
    def _detect_language(self, file_path: str) -> str:
        """Detect language from extension"""
        ext = Path(file_path).suffix.lower()
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
        }
        return lang_map.get(ext, 'unknown')
    
    def _detect_naming_convention(self, name: str) -> str:
        """Detect naming convention type"""
        if not name or name.startswith('_'):
            return 'unknown'
        
        # snake_case
        if '_' in name and name.islower():
            return 'snake_case'
        
        # UPPER_SNAKE_CASE (constants)
        if '_' in name and name.isupper():
            return 'UPPER_SNAKE_CASE'
        
        # PascalCase
        if name[0].isupper() and '_' not in name:
            return 'PascalCase'
        
        # camelCase
        if name[0].islower() and '_' not in name and any(c.isupper() for c in name):
            return 'camelCase'
        
        # lowercase
        if name.islower() and '_' not in name:
            return 'lowercase'
        
        return 'mixed'
    
    def _extract_identifiers(self, tree_node, source_code: bytes, id_type: str) -> List[str]:
        """Extract identifiers of specific type (function, class, variable)"""
        identifiers = []
        
        # Python patterns
        if id_type == 'function' and tree_node.type in ['function_definition', 'function_declaration']:
            for child in tree_node.children:
                if child.type == 'identifier':
                    name = source_code[child.start_byte:child.end_byte].decode('utf-8')
                    identifiers.append(name)
                    break
        
        elif id_type == 'class' and tree_node.type == 'class_definition':
            for child in tree_node.children:
                if child.type == 'identifier':
                    name = source_code[child.start_byte:child.end_byte].decode('utf-8')
                    identifiers.append(name)
                    break
        
        # Recursively process children
        for child in tree_node.children:
            identifiers.extend(self._extract_identifiers(child, source_code, id_type))
        
        return identifiers
    
    def _extract_imports(self, tree_node, source_code: bytes, language: str) -> List[str]:
        """Extract import statements"""
        imports = []
        
        if language == 'python':
            if tree_node.type in ['import_statement', 'import_from_statement']:
                import_text = source_code[tree_node.start_byte:tree_node.end_byte].decode('utf-8')
                
                # Extract module names
                if 'from' in import_text:
                    match = re.search(r'from\s+([\w.]+)', import_text)
                    if match:
                        imports.append(match.group(1))
                elif 'import' in import_text:
                    modules = re.findall(r'import\s+([\w.,\s]+)', import_text)
                    for module_list in modules:
                        for module in module_list.split(','):
                            module = module.strip().split(' as ')[0]
                            if module:
                                imports.append(module)
        
        else:  # JavaScript/TypeScript
            if tree_node.type == 'import_statement':
                import_text = source_code[tree_node.start_byte:tree_node.end_byte].decode('utf-8')
                match = re.search(r'from\s+["\']([^"\']+)["\']', import_text)
                if match:
                    imports.append(match.group(1))
        
        # Recursively search
        for child in tree_node.children:
            imports.extend(self._extract_imports(child, source_code, language))
        
        return imports
    
    def _check_async_usage(self, source_code: str, language: str) -> bool:
        """Check if file uses async/await"""
        if language == 'python':
            return 'async def' in source_code or 'await ' in source_code
        else:
            return 'async ' in source_code or 'await ' in source_code
    
    def _check_type_hints(self, source_code: str, language: str) -> bool:
        """Check if file uses type hints/annotations"""
        if language == 'python':
            return '->' in source_code or ': ' in source_code
        else:
            return ': ' in source_code and 'interface' in source_code or 'type ' in source_code
    
    def analyze_repository_style(self, repo_path: str) -> Dict:
        """Analyze coding style patterns across repository"""
        repo_path = Path(repo_path)
        
        print(f"🎨 Analyzing code style for repository...")
        
        # Discover code files
        code_files = []
        extensions = {'.py', '.js', '.jsx', '.ts', '.tsx'}
        skip_dirs = {'node_modules', '.git', '__pycache__', 'venv', 'env', 'dist', 'build'}
        
        for file_path in repo_path.rglob('*'):
            if file_path.is_dir():
                continue
            if any(skip in file_path.parts for skip in skip_dirs):
                continue
            if file_path.suffix in extensions:
                code_files.append(file_path)
        
        # Collect style data
        function_names = []
        class_names = []
        all_imports = []
        async_files = 0
        typed_files = 0
        total_files = 0
        language_dist = Counter()
        
        for file_path in code_files:
            language = self._detect_language(str(file_path))
            if language not in self.parsers:
                continue
            
            try:
                with open(file_path, 'rb') as f:
                    source_code = f.read()
                
                source_text = source_code.decode('utf-8')
                tree = self.parsers[language].parse(source_code)
                
                # Extract identifiers
                functions = self._extract_identifiers(tree.root_node, source_code, 'function')
                classes = self._extract_identifiers(tree.root_node, source_code, 'class')
                imports = self._extract_imports(tree.root_node, source_code, language)
                
                function_names.extend(functions)
                class_names.extend(classes)
                all_imports.extend(imports)
                
                # Check for async and type usage
                if self._check_async_usage(source_text, language):
                    async_files += 1
                
                if self._check_type_hints(source_text, language):
                    typed_files += 1
                
                total_files += 1
                language_dist[language] += 1
                
            except Exception as e:
                print(f"Error analyzing {file_path}: {e}")
                continue
        
        # Analyze naming conventions
        function_conventions = Counter([self._detect_naming_convention(name) for name in function_names])
        class_conventions = Counter([self._detect_naming_convention(name) for name in class_names])
        
        # Most common imports
        import_freq = Counter(all_imports)
        top_imports = import_freq.most_common(20)
        
        # Calculate percentages
        total_functions = len(function_names)
        total_classes = len(class_names)
        
        print(f"✅ Style analysis complete!")
        print(f"   • {total_files} files analyzed")
        print(f"   • {total_functions} functions found")
        print(f"   • {total_classes} classes found")
        
        return {
            "summary": {
                "total_files_analyzed": total_files,
                "total_functions": total_functions,
                "total_classes": total_classes,
                "async_adoption": f"{(async_files/total_files*100):.0f}%" if total_files > 0 else "0%",
                "type_hints_usage": f"{(typed_files/total_files*100):.0f}%" if total_files > 0 else "0%"
            },
            "naming_conventions": {
                "functions": {
                    conv: {
                        "count": count,
                        "percentage": f"{(count/total_functions*100):.1f}%" if total_functions > 0 else "0%"
                    }
                    for conv, count in function_conventions.most_common(5)
                },
                "classes": {
                    conv: {
                        "count": count,
                        "percentage": f"{(count/total_classes*100):.1f}%" if total_classes > 0 else "0%"
                    }
                    for conv, count in class_conventions.most_common(5)
                }
            },
            "language_distribution": {
                lang: {
                    "count": count,
                    "percentage": f"{(count/total_files*100):.1f}%" if total_files > 0 else "0%"
                }
                for lang, count in language_dist.most_common()
            },
            "top_imports": [
                {"module": module, "count": count}
                for module, count in top_imports
            ],
            "patterns": {
                "async_usage": f"{async_files}/{total_files} files use async",
                "type_annotations": f"{typed_files}/{total_files} files use type hints",
                "async_percentage": (async_files/total_files*100) if total_files > 0 else 0,
                "typed_percentage": (typed_files/total_files*100) if total_files > 0 else 0
            }
        }

    
    # ===== SUPABASE CACHING =====
    
    def save_to_cache(self, repo_id: str, style_data: Dict):
        """Save style analysis to Supabase for caching"""
        from services.supabase_service import get_supabase_service
        
        db = get_supabase_service()
        
        # Group by language
        for language, data in style_data.get("languages", {}).items():
            analysis = {
                "naming_convention": data.get("naming_conventions"),
                "async_usage": data.get("async_usage"),
                "type_hints": data.get("type_hints"),
                "common_imports": style_data.get("top_imports", []),
                "patterns": style_data.get("patterns", {})
            }
            
            db.upsert_code_style(repo_id, language, analysis)
        
        print(f"✅ Cached code style analysis for {repo_id} in Supabase")
    
    def load_from_cache(self, repo_id: str) -> Dict:
        """Load style analysis from Supabase cache"""
        from services.supabase_service import get_supabase_service
        
        db = get_supabase_service()
        
        # Get cached style analysis
        cached_styles = db.get_code_style(repo_id)
        
        if not cached_styles:
            return None
        
        # Reconstruct style data
        languages = {}
        common_imports = []
        patterns = {}
        
        for style in cached_styles:
            language = style["language"]
            languages[language] = {
                "naming_conventions": style.get("naming_convention", {}),
                "async_usage": style.get("async_usage", {}),
                "type_hints": style.get("type_hints", {})
            }
            
            if style.get("common_imports"):
                common_imports = style["common_imports"]
            
            if style.get("patterns"):
                patterns = style["patterns"]
        
        print(f"✅ Loaded cached code style for {repo_id} from Supabase")
        
        return {
            "languages": languages,
            "top_imports": common_imports,
            "patterns": patterns
        }
