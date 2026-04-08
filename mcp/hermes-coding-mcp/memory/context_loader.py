"""
Context Loader — Read Path for Session Start

Loads relevant context from the memory graph at session start
and injects it into the system prompt.
"""

from pathlib import Path
from typing import Optional, Dict, List, Any
import json

from .graph_db import KnowledgeGraph
from .pattern_lib import PatternLibrary


class ContextLoader:
    """
    Loads memory context at session start for injection into prompts.
    
    Read path:
    1. Load repo context from SQLite graph
    2. Retrieve recent observations about project
    3. Load relevant patterns from pattern library
    4. Inject into system prompt as context
    """
    
    def __init__(
        self,
        repo_path: str,
        db_path: Optional[str] = None,
        patterns_dir: Optional[Path] = None
    ):
        """
        Initialize the context loader.
        
        Args:
            repo_path: Path to the repository being worked on
            db_path: Optional custom path for the knowledge graph DB
            patterns_dir: Optional custom path for patterns directory
        """
        self.repo_path = Path(repo_path).resolve()
        self.kg = KnowledgeGraph(db_path)
        self.pl = PatternLibrary(patterns_dir)
        
        self.session_id: Optional[str] = None
        self.context: Dict[str, Any] = {}
    
    def load_context(self) -> Dict[str, Any]:
        """
        Load all relevant context for this session.
        
        Returns:
            Dict containing:
            - repo_info: Repository metadata
            - recent_sessions: Previous session summaries
            - patterns: Relevant code patterns
            - observations: Recent observations about the codebase
            - dependency_hints: Known dependencies
        """
        with self.kg:
            # Start a new session
            self.session_id = self.kg.start_session(str(self.repo_path))
            
            # Load context components
            self.context = {
                "session_id": self.session_id,
                "repo_info": self._get_repo_info(),
                "recent_sessions": self._get_recent_sessions(),
                "relevant_patterns": self._get_relevant_patterns(),
                "observations": self._get_recent_observations(),
                "dependency_hints": self._get_dependency_hints(),
                "file_structure": self._get_file_structure(),
            }
        
        return self.context
    
    def _get_repo_info(self) -> Dict[str, Any]:
        """Get repository information from the graph."""
        # Find repo root node if it exists
        repo_nodes = self.kg.find_nodes(
            node_type="module",
            name_pattern=str(self.repo_path)
        )
        
        if repo_nodes:
            return {
                "name": self.repo_path.name,
                "path": str(self.repo_path),
                "known": True,
                "root_node_id": repo_nodes[0]["id"]
            }
        
        return {
            "name": self.repo_path.name,
            "path": str(self.repo_path),
            "known": False
        }
    
    def _get_recent_sessions(self) -> List[Dict[str, Any]]:
        """Get recent session summaries."""
        sessions = self.kg.get_recent_sessions(str(self.repo_path), limit=3)
        
        return [
            {
                "tasks_completed": s["tasks_completed"],
                "key_decisions": s.get("key_decisions", []),
                "date": s["started_at"]
            }
            for s in sessions
        ]
    
    def _get_relevant_patterns(self) -> List[Dict[str, Any]]:
        """Get patterns relevant to this repository."""
        patterns = []
        
        # Detect languages in repo
        languages = self._detect_languages()
        
        for lang in languages:
            lang_patterns = self.pl.list_patterns(language=lang)
            patterns.extend(lang_patterns[:5])  # Top 5 per language
        
        return patterns
    
    def _detect_languages(self) -> List[str]:
        """Detect programming languages in the repo."""
        languages = set()
        extensions = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
        }
        
        for ext, lang in extensions.items():
            if list(self.repo_path.rglob(f"*{ext}")):
                languages.add(lang)
        
        return list(languages)
    
    def _get_recent_observations(self) -> List[Dict[str, Any]]:
        """Get recent observations about the codebase."""
        # Get observations for nodes in this repo
        repo_nodes = self.kg.find_nodes(
            path_prefix=str(self.repo_path)
        )
        
        observations = []
        for node in repo_nodes[:20]:  # Limit to 20 most relevant
            node_obs = self.kg.get_observations(
                node_id=node["id"],
                min_confidence=0.7
            )
            observations.extend(node_obs)
        
        # Sort by confidence and limit
        observations.sort(key=lambda x: x["confidence"], reverse=True)
        return observations[:15]
    
    def _get_dependency_hints(self) -> Dict[str, List[str]]:
        """Get known dependency hints from the graph."""
        hints = {}
        
        # Look for import relationships
        repo_nodes = self.kg.find_nodes(path_prefix=str(self.repo_path))
        
        for node in repo_nodes:
            outgoing = self.kg.get_outgoing_edges(node["id"])
            
            imports = [
                e["target_name"] for e in outgoing 
                if e["relationship"] == "imports"
            ]
            
            if imports:
                hints[node["name"]] = imports
        
        return hints
    
    def _get_file_structure(self) -> Dict[str, Any]:
        """Get known file structure hints."""
        # Get file nodes for this repo
        file_nodes = self.kg.find_nodes(
            node_type="file",
            path_prefix=str(self.repo_path)
        )
        
        return {
            "known_files": len(file_nodes),
            "top_level": [
                {"name": n["name"], "path": n["path"]}
                for n in file_nodes[:20]
            ]
        }
    
    def format_for_prompt(self) -> str:
        """
        Format the loaded context as a string for prompt injection.
        
        Returns:
            Formatted context string
        """
        if not self.context:
            self.load_context()
        
        lines = [
            "## Repository Context (from memory)",
            "",
        ]
        
        # Repo info
        repo_info = self.context.get("repo_info", {})
        lines.append(f"**Repository:** {repo_info.get('name', 'unknown')}")
        if repo_info.get("known"):
            lines.append("- This is a known repository we've worked on before")
        
        # Recent sessions
        recent = self.context.get("recent_sessions", [])
        if recent:
            lines.append("")
            lines.append("### Recent Sessions")
            for session in recent:
                lines.append(f"- Completed {session['tasks_completed']} tasks")
                if session.get("key_decisions"):
                    lines.append(f"  Key decisions: {', '.join(session['key_decisions'][:3])}")
        
        # Patterns
        patterns = self.context.get("relevant_patterns", [])
        if patterns:
            lines.append("")
            lines.append("### Known Code Patterns")
            for p in patterns[:5]:
                lines.append(f"- **{p['name']}** ({p['language']}): {p.get('description', '')}")
        
        # Observations
        observations = self.context.get("observations", [])
        if observations:
            lines.append("")
            lines.append("### Codebase Observations")
            for obs in observations[:5]:
                lines.append(f"- [{obs['observation_type']}] {obs['content']} (confidence: {obs['confidence']:.0%})")
        
        # Dependency hints
        hints = self.context.get("dependency_hints", {})
        if hints:
            lines.append("")
            lines.append("### Known Dependencies")
            for name, deps in list(hints.items())[:10]:
                lines.append(f"- `{name}` imports: {', '.join(deps[:5])}")
        
        lines.append("")
        lines.append("---\n")
        
        return "\n".join(lines)
    
    def get_session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self.session_id
    
    def close(self) -> None:
        """Close connections."""
        self.kg.close()
