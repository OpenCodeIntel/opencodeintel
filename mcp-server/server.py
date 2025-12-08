#!/usr/bin/env python3
"""
CodeIntel MCP Server
Provides codebase intelligence tools for LLMs via Model Context Protocol
"""
import asyncio
import os
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
from dotenv import load_dotenv

# Import API config (single source of truth for versioning)
from config import API_PREFIX

# Load environment variables
load_dotenv()

# Configuration
BACKEND_BASE_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")
BACKEND_API_URL = f"{BACKEND_BASE_URL}{API_PREFIX}"  # Full versioned URL
API_KEY = os.getenv("API_KEY", "dev-secret-key")

# Create MCP server instance
server = Server("codeintel-mcp")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools for codebase intelligence"""
    return [
        types.Tool(
            name="search_code",
            description="Semantically search code in a repository. Finds code by meaning, not just keywords. Use this to find existing implementations, patterns, or specific functionality.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (natural language or code snippet). Examples: 'authentication middleware', 'React hook for state', 'database connection pool'"
                    },
                    "repo_id": {
                        "type": "string",
                        "description": "Repository identifier"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "default": 10
                    }
                },
                "required": ["query", "repo_id"]
            }
        ),
        types.Tool(
            name="list_repositories",
            description="List all indexed repositories available for analysis",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="get_dependency_graph",
            description="Get the complete dependency graph for a repository. Shows which files depend on which, identifies critical files, and reveals architecture patterns.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "Repository identifier"
                    }
                },
                "required": ["repo_id"]
            }
        ),
        types.Tool(
            name="analyze_code_style",
            description="Analyze team coding patterns and conventions. Returns naming conventions (snake_case vs camelCase), async usage, type hint usage, common imports, and coding patterns. Use this to match team style when generating code.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "Repository identifier"
                    }
                },
                "required": ["repo_id"]
            }
        ),
        types.Tool(
            name="analyze_impact",
            description="Analyze the impact of changing a specific file. Shows what files depend on it, what it depends on, risk level, and related test files. Critical for understanding change consequences.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "Repository identifier"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to analyze (relative to repo root)"
                    }
                },
                "required": ["repo_id", "file_path"]
            }
        ),
        types.Tool(
            name="get_repository_insights",
            description="Get comprehensive insights about a repository including dependency metrics, code style summary, and architecture overview. Use this for high-level codebase understanding.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_id": {
                        "type": "string",
                        "description": "Repository identifier"
                    }
                },
                "required": ["repo_id"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution"""
    
    if arguments is None:
        arguments = {}
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            headers = {"Authorization": f"Bearer {API_KEY}"}
            
            if name == "search_code":
                response = await client.post(
                    f"{BACKEND_API_URL}/search",
                    json=arguments,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                # Format results
                formatted = f"# Code Search Results\n\n"
                formatted += f"Found {result.get('count', 0)} results"
                if result.get('cached'):
                    formatted += " (⚡ cached)\n\n"
                else:
                    formatted += "\n\n"
                
                if result.get("results"):
                    for idx, res in enumerate(result["results"], 1):
                        formatted += f"## {idx}. {res.get('name', 'unknown')} ({res.get('score', 0)*100:.0f}% match)\n"
                        formatted += f"**File:** `{res.get('file_path', 'unknown')}`\n"
                        formatted += f"**Type:** {res.get('type', 'unknown')} | **Language:** {res.get('language', 'unknown')}\n"
                        formatted += f"**Lines:** {res.get('line_start', 0)}-{res.get('line_end', 0)}\n\n"
                        formatted += f"```{res.get('language', 'python')}\n{res.get('code', '')}\n```\n\n"
                else:
                    formatted += "No results found.\n"
                
                return [types.TextContent(type="text", text=formatted)]
            
            elif name == "list_repositories":
                response = await client.get(
                    f"{BACKEND_API_URL}/repos",
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                repo_list = "# Indexed Repositories\n\n"
                if result.get("repositories"):
                    for repo in result["repositories"]:
                        repo_list += f"### {repo.get('name', 'unknown')}\n"
                        repo_list += f"- **ID:** `{repo.get('id')}`\n"
                        repo_list += f"- **Status:** {repo.get('status', 'unknown')}\n"
                        repo_list += f"- **Functions:** {repo.get('file_count', 0):,}\n"
                        repo_list += f"- **Branch:** {repo.get('branch', 'main')}\n\n"
                else:
                    repo_list += "No repositories indexed yet.\n"
                
                return [types.TextContent(type="text", text=repo_list)]
            
            elif name == "get_dependency_graph":
                response = await client.get(
                    f"{BACKEND_API_URL}/repos/{arguments['repo_id']}/dependencies",
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                formatted = f"# Dependency Graph Analysis\n\n"
                formatted += f"**Total Files:** {result.get('total_files', 0)}\n"
                formatted += f"**Total Dependencies:** {result.get('total_dependencies', 0)}\n"
                formatted += f"**Avg Dependencies per File:** {result.get('metrics', {}).get('avg_dependencies', 0):.1f}\n\n"
                
                if result.get('metrics', {}).get('most_critical_files'):
                    formatted += "## Most Critical Files (High Impact)\n\n"
                    for item in result['metrics']['most_critical_files'][:5]:
                        formatted += f"- `{item['file']}` - **{item['dependents']} dependents**\n"
                    formatted += "\n"
                
                if result.get('external_dependencies'):
                    formatted += f"## External Dependencies\n\n"
                    for dep in result['external_dependencies'][:10]:
                        formatted += f"- {dep}\n"
                
                return [types.TextContent(type="text", text=formatted)]
            
            elif name == "analyze_code_style":
                response = await client.get(
                    f"{BACKEND_API_URL}/repos/{arguments['repo_id']}/style-analysis",
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                formatted = f"# Code Style Analysis\n\n"
                
                summary = result.get('summary', {})
                formatted += f"**Files Analyzed:** {summary.get('total_files_analyzed', 0)}\n"
                formatted += f"**Functions:** {summary.get('total_functions', 0)}\n"
                formatted += f"**Async Adoption:** {summary.get('async_adoption', '0%')}\n"
                formatted += f"**Type Hints:** {summary.get('type_hints_usage', '0%')}\n\n"
                
                # Naming conventions
                if result.get('naming_conventions', {}).get('functions'):
                    formatted += "## Function Naming Conventions\n\n"
                    for conv, info in result['naming_conventions']['functions'].items():
                        formatted += f"- **{conv}:** {info['percentage']} ({info['count']} functions)\n"
                    formatted += "\n"
                
                # Top imports
                if result.get('top_imports'):
                    formatted += "## Most Common Imports\n\n"
                    for item in result['top_imports'][:10]:
                        formatted += f"- `{item['module']}` (used {item['count']}×)\n"
                
                return [types.TextContent(type="text", text=formatted)]
            
            elif name == "analyze_impact":
                response = await client.post(
                    f"{BACKEND_API_URL}/repos/{arguments['repo_id']}/impact",
                    json={"repo_id": arguments['repo_id'], "file_path": arguments['file_path']},
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                formatted = f"# Impact Analysis: {result.get('file', 'unknown')}\n\n"
                formatted += f"**Risk Level:** {result.get('risk_level', 'unknown').upper()}\n"
                formatted += f"**Impact Summary:** {result.get('impact_summary', '')}\n\n"
                
                formatted += f"## Dependencies ({len(result.get('direct_dependencies', []))})\n"
                formatted += "Files this file imports:\n"
                for dep in result.get('direct_dependencies', [])[:10]:
                    formatted += f"- `{dep}`\n"
                formatted += "\n"
                
                formatted += f"## Dependents ({len(result.get('all_dependents', []))})\n"
                formatted += "Files that would be affected by changes:\n"
                for dep in result.get('all_dependents', [])[:15]:
                    formatted += f"- `{dep}`\n"
                
                if result.get('test_files'):
                    formatted += f"\n## Related Tests\n"
                    for test in result['test_files']:
                        formatted += f"- `{test}`\n"
                
                return [types.TextContent(type="text", text=formatted)]
            
            elif name == "get_repository_insights":
                response = await client.get(
                    f"{BACKEND_API_URL}/repos/{arguments['repo_id']}/insights",
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                formatted = f"# Repository Insights: {result.get('name', 'unknown')}\n\n"
                formatted += f"**Status:** {result.get('status', 'unknown')}\n"
                formatted += f"**Functions Indexed:** {result.get('functions_indexed', 0):,}\n"
                formatted += f"**Total Files:** {result.get('total_files', 0)}\n"
                formatted += f"**Total Dependencies:** {result.get('total_dependencies', 0)}\n\n"
                
                metrics = result.get('graph_metrics', {})
                if metrics.get('most_critical_files'):
                    formatted += "## Most Critical Files\n"
                    for item in metrics['most_critical_files'][:5]:
                        formatted += f"- `{item['file']}` ({item['dependents']} dependents)\n"
                
                return [types.TextContent(type="text", text=formatted)]
            
            else:
                raise ValueError(f"Unknown tool: {name}")
                
    except httpx.HTTPError as e:
        error_msg = f"API Error: {str(e)}"
        return [types.TextContent(type="text", text=error_msg)]
    except Exception as e:
        error_msg = f"Error executing tool: {str(e)}"
        return [types.TextContent(type="text", text=error_msg)]


async def main():
    """Run the MCP server"""
    from mcp.server.models import ServerCapabilities
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="codeintel-mcp",
                server_version="0.3.0",
                capabilities=ServerCapabilities(
                    tools={}
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
