"""
Dependency Analyzer
Extracts imports and builds dependency graph for codebase understanding
"""
from pathlib import Path
from typing import List, Dict, Set
import re

# Tree-sitter
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Parser

from services.observability import logger, capture_exception, track_time, metrics


class DependencyAnalyzer:
    """Analyze code dependencies and build dependency graph"""
    
    def __init__(self):
        # Initialize parsers
        self.parsers = {
            'python': Parser(Language(tspython.language())),
            'javascript': Parser(Language(tsjavascript.language())),
            'typescript': Parser(Language(tsjavascript.language())),
        }
        logger.info("DependencyAnalyzer initialized")
    
    def _detect_language(self, file_path: str) -> str:
        """Detect language from file extension"""
        ext = Path(file_path).suffix.lower()
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
        }
        return lang_map.get(ext, 'unknown')
    
    def _extract_python_imports(self, tree_node, source_code: bytes) -> Set[str]:
        """Extract import statements from Python AST"""
        imports = set()
        
        if tree_node.type in ['import_statement', 'import_from_statement']:
            import_text = source_code[tree_node.start_byte:tree_node.end_byte].decode('utf-8')
            
            if import_text.startswith('from'):
                match = re.match(r'from\s+([\w.]+)\s+import', import_text)
                if match:
                    imports.add(match.group(1))
            elif import_text.startswith('import'):
                modules = re.findall(r'import\s+([\w.,\s]+)', import_text)
                if modules:
                    for module_list in modules:
                        for module in module_list.split(','):
                            module = module.strip().split(' as ')[0]
                            if module:
                                imports.add(module)
        
        for child in tree_node.children:
            imports.update(self._extract_python_imports(child, source_code))
        
        return imports
    
    def _extract_js_imports(self, tree_node, source_code: bytes) -> Set[str]:
        """Extract import statements from JavaScript/TypeScript AST"""
        imports = set()
        
        if tree_node.type == 'import_statement':
            import_text = source_code[tree_node.start_byte:tree_node.end_byte].decode('utf-8')
            matches = re.findall(r'from\s+["\']([^"\']+)["\']', import_text)
            if not matches:
                matches = re.findall(r'import\s+["\']([^"\']+)["\']', import_text)
            for match in matches:
                imports.add(match)
        
        if tree_node.type == 'export_statement':
            export_text = source_code[tree_node.start_byte:tree_node.end_byte].decode('utf-8')
            matches = re.findall(r'from\s+["\']([^"\']+)["\']', export_text)
            for match in matches:
                imports.add(match)
        
        if tree_node.type == 'call_expression':
            call_text = source_code[tree_node.start_byte:tree_node.end_byte].decode('utf-8')
            if 'require(' in call_text:
                match = re.search(r'require\(["\']([^"\']+)["\']\)', call_text)
                if match:
                    imports.add(match.group(1))
        
        for child in tree_node.children:
            imports.update(self._extract_js_imports(child, source_code))
        
        return imports
    
    def analyze_file_dependencies(self, file_path: str) -> Dict:
        """Analyze a single file's dependencies"""
        language = self._detect_language(file_path)
        
        if language not in self.parsers:
            return {"file": file_path, "imports": [], "language": language}
        
        try:
            with open(file_path, 'rb') as f:
                source_code = f.read()
            
            tree = self.parsers[language].parse(source_code)
            
            if language == 'python':
                imports = self._extract_python_imports(tree.root_node, source_code)
            else:
                imports = self._extract_js_imports(tree.root_node, source_code)
            
            return {
                "file": str(file_path),
                "imports": list(imports),
                "language": language,
                "import_count": len(imports)
            }
            
        except Exception as e:
            logger.error("Error analyzing file", file_path=file_path, error=str(e))
            return {"file": str(file_path), "imports": [], "language": language, "error": str(e)}
    
    def build_dependency_graph(self, repo_path: str) -> Dict:
        """Build complete dependency graph for repository"""
        repo_path = Path(repo_path)
        
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
        
        logger.info("Building dependency graph", file_count=len(code_files))
        
        # Analyze each file
        file_dependencies = {}
        all_imports = set()
        
        for file_path in code_files:
            relative_path = str(file_path.relative_to(repo_path))
            analysis = self.analyze_file_dependencies(str(file_path))
            
            file_dependencies[relative_path] = analysis['imports']
            all_imports.update(analysis['imports'])
        
        # Build graph structure
        nodes = []
        edges = []
        internal_files = set(file_dependencies.keys())
        
        # DEBUG: Show sample of what we're working with
        sample_files = list(internal_files)[:3]
        logger.debug("Sample internal files", sample=sample_files)
        
        # Find a file with imports to debug
        for f, imports in list(file_dependencies.items())[:5]:
            if imports:
                logger.debug("Sample file imports", file=f, imports=imports[:3])
                break
        
        # Create nodes
        for file_path in file_dependencies.keys():
            language = self._detect_language(file_path)
            nodes.append({
                "id": file_path,
                "label": Path(file_path).name,
                "type": "file",
                "language": language,
                "import_count": len(file_dependencies[file_path])
            })
        
        # Create edges
        resolved_count = 0
        failed_count = 0
        for source_file, imports in file_dependencies.items():
            for imported_module in imports:
                target_file = self._resolve_import_to_file(
                    imported_module, 
                    source_file,
                    internal_files,
                    repo_path
                )
                
                if target_file:
                    resolved_count += 1
                    edges.append({
                        "source": source_file,
                        "target": target_file,
                        "type": "import"
                    })
                else:
                    failed_count += 1
        
        logger.info("Import resolution complete", resolved=resolved_count, external=failed_count)
        
        # Calculate metrics
        graph_metrics = self._calculate_graph_metrics(file_dependencies, edges)
        
        logger.info("Dependency graph built", nodes=len(nodes), edges=len(edges))
        metrics.increment("dependency_graphs_built")
        
        return {
            "nodes": nodes,
            "edges": edges,
            "dependencies": file_dependencies,  # Added for Supabase caching
            "metrics": graph_metrics,
            "total_files": len(nodes),
            "total_dependencies": len(edges),
            "external_dependencies": list(all_imports - set(internal_files))[:50]
        }

    def _resolve_import_to_file(
        self,
        import_path: str,
        source_file: str,
        internal_files: Set[str],
        repo_path: Path
    ) -> str:
        """Resolve an import to an actual file in the repo"""
        
        # External dependency check
        if not import_path.startswith('.') and not import_path.startswith('/'):
            # Might still be internal for Python packages
            if '/' not in import_path:
                return None
        
        source_path = Path(source_file)
        source_dir = source_path.parent
        
        # Relative imports
        if import_path.startswith('.'):
            clean_import = import_path.lstrip('./')
            
            levels_up = import_path.count('../')
            if levels_up > 0:
                clean_import = import_path.replace('../', '', levels_up)
                target_dir = source_dir
                for _ in range(levels_up):
                    target_dir = target_dir.parent
                potential_base = target_dir / clean_import
            else:
                potential_base = source_dir / clean_import
            
            extensions = ['', '.ts', '.tsx', '.js', '.jsx', '.py']
            
            for ext in extensions:
                # Build the potential path
                test_path = str(potential_base) + ext
                
                # Check if this relative path exists in internal files
                if test_path in internal_files:
                    return test_path
                
                # Try with /index
                index_path = str(potential_base / ('index' + ext))
                if index_path in internal_files:
                    return index_path
        
        # Python absolute imports
        if not import_path.startswith('.'):
            module_path = import_path.replace('.', '/')
            
            for ext in ['.py', '.js', '.ts']:
                test_path = module_path + ext
                if test_path in internal_files:
                    return test_path
                
                init_path = f"{module_path}/__init__.py"
                if init_path in internal_files:
                    return init_path
        
        return None
    
    def _calculate_graph_metrics(self, dependencies: Dict, edges: List) -> Dict:
        """Calculate graph metrics"""
        in_degree = {}
        out_degree = {}
        
        for edge in edges:
            source = edge['source']
            target = edge['target']
            
            out_degree[source] = out_degree.get(source, 0) + 1
            in_degree[target] = in_degree.get(target, 0) + 1
        
        most_critical = sorted(
            [(file, degree) for file, degree in in_degree.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        most_complex = sorted(
            [(file, degree) for file, degree in out_degree.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            "most_critical_files": [{"file": f, "dependents": d} for f, d in most_critical],
            "most_complex_files": [{"file": f, "dependencies": d} for f, d in most_complex],
            "avg_dependencies": sum(out_degree.values()) / len(out_degree) if out_degree else 0,
            "total_edges": len(edges)
        }
    
    def get_file_impact(self, repo_path: str, file_path: str, graph_data: Dict) -> Dict:
        """Calculate impact of changing a specific file"""
        dependents_map = {}
        dependencies_map = {}
        
        for edge in graph_data['edges']:
            source = edge['source']
            target = edge['target']
            
            if target not in dependents_map:
                dependents_map[target] = []
            dependents_map[target].append(source)
            
            if source not in dependencies_map:
                dependencies_map[source] = []
            dependencies_map[source].append(target)
        
        direct_dependents = dependents_map.get(file_path, [])
        all_dependents = self._find_transitive_dependents(file_path, dependents_map)
        direct_dependencies = dependencies_map.get(file_path, [])
        
        # Calculate risk based on impact
        risk_level = "low"
        if len(all_dependents) > 10:
            risk_level = "high"
        elif len(all_dependents) > 3:
            risk_level = "medium"
        
        # Generate better impact summary
        if len(all_dependents) == 0:
            impact_msg = "No files depend on this - safe to modify"
        elif len(all_dependents) == 1:
            impact_msg = "1 file would be affected by changes"
        else:
            impact_msg = f"{len(all_dependents)} files would be affected by changes"
        
        test_files = self._find_test_files(file_path, graph_data['nodes'])
        
        return {
            "file": file_path,
            "direct_dependents": direct_dependents,
            "all_dependents": all_dependents,
            "dependent_count": len(all_dependents),
            "direct_dependencies": direct_dependencies,
            "dependency_count": len(direct_dependencies),
            "risk_level": risk_level,
            "test_files": test_files,
            "impact_summary": impact_msg
        }
    
    def _find_transitive_dependents(self, file_path: str, dependents_map: Dict) -> List[str]:
        """Find all files that transitively depend on this file (BFS)"""
        visited = set()
        queue = [file_path]
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            
            visited.add(current)
            
            for dependent in dependents_map.get(current, []):
                if dependent not in visited:
                    queue.append(dependent)
        
        visited.discard(file_path)
        return list(visited)
    
    def _find_test_files(self, file_path: str, nodes: List[Dict]) -> List[str]:
        """Find test files related to this file"""
        file_name = Path(file_path).stem
        test_patterns = [
            f"test_{file_name}",
            f"{file_name}_test",
            f"{file_name}.test",
            f"{file_name}.spec"
        ]
        
        test_files = []
        for node in nodes:
            node_name = Path(node['id']).stem
            if any(pattern in node_name for pattern in test_patterns):
                test_files.append(node['id'])
        
        return test_files

    
    # ===== SUPABASE CACHING =====
    
    def save_to_cache(self, repo_id: str, graph_data: Dict):
        """Save dependency graph to Supabase for caching"""
        from services.supabase_service import get_supabase_service
        
        db = get_supabase_service()
        
        # Prepare file dependencies for bulk insert
        file_deps = []
        dependencies = graph_data.get("dependencies", {})
        edges = graph_data.get("edges", [])
        
        # Build a map of which files each file depends on (resolved internal only)
        internal_deps_map = {}
        for edge in edges:
            source = edge['source']
            target = edge['target']
            if source not in internal_deps_map:
                internal_deps_map[source] = []
            internal_deps_map[source].append(target)
        
        for file_path, imports in dependencies.items():
            # Get resolved internal dependencies for this file
            internal_deps = internal_deps_map.get(file_path, [])
            
            # Build reverse dependencies
            depended_by = []
            for other_file, other_deps in internal_deps_map.items():
                if file_path in other_deps:
                    depended_by.append(other_file)
            
            file_deps.append({
                "file_path": file_path,
                "depends_on": internal_deps,  # Save resolved internal deps, not raw imports
                "depended_by": depended_by,
                "import_count": len(imports),
                "dependent_count": len(depended_by)
            })
        
        # Clear old dependencies
        db.clear_file_dependencies(repo_id)
        
        # Bulk insert new dependencies
        logger.info("Saving file dependencies to Supabase", repo_id=repo_id, count=len(file_deps))
        db.upsert_file_dependencies(repo_id, file_deps)
        
        # Save repository insights
        metrics = graph_data.get("metrics", {})
        insights = {
            "total_files": len(dependencies),
            "total_dependencies": sum(len(deps) for deps in dependencies.values()),
            "avg_dependencies_per_file": metrics.get("avg_dependencies", 0),
            "max_dependencies": max((len(deps) for deps in dependencies.values()), default=0),
            "critical_files": [f["file"] for f in metrics.get("most_critical_files", [])[:10]],
            "architecture_patterns": {
                "most_complex": metrics.get("most_complex_files", [])
            }
        }
        
        db.upsert_repository_insights(repo_id, insights)
        logger.info("Cached dependency graph in Supabase", repo_id=repo_id)
    
    def load_from_cache(self, repo_id: str) -> Dict:
        """Load dependency graph from Supabase cache"""
        from services.supabase_service import get_supabase_service
        
        db = get_supabase_service()
        
        # Get file dependencies
        file_deps = db.get_file_dependencies(repo_id)
        logger.debug("Loading cache", repo_id=repo_id, found=len(file_deps) if file_deps else 0)
        
        if not file_deps:
            return None
        
        # Reconstruct dependency graph
        dependencies = {}
        for dep in file_deps:
            dependencies[dep["file_path"]] = dep["depends_on"]
        
        # Build edges for graph
        edges = []
        for file_path, imports in dependencies.items():
            for imported in imports:
                if imported in dependencies:  # Only internal dependencies
                    edges.append({"source": file_path, "target": imported})
        
        # Get insights
        insights = db.get_repository_insights(repo_id)
        
        metrics = {
            "avg_dependencies": insights.get("avg_dependencies_per_file", 0) if insights else 0,
            "total_edges": len(edges)
        }
        
        logger.info("Loaded cached dependency graph", repo_id=repo_id)
        
        return {
            "dependencies": dependencies,
            "edges": edges,
            "metrics": metrics,
            "nodes": [{"id": f, "imports": len(imports)} for f, imports in dependencies.items()]
        }
