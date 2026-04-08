"""
Pattern Library — Layer 2: File-based Pattern Storage

Stores successful code patterns for reuse across sessions.
Patterns are organized by language and type for easy retrieval.
"""

import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime


class PatternLibrary:
    """
    File-based pattern library for storing and retrieving code patterns.
    
    Directory structure:
        brain/patterns/
        ├── python/
        │   ├── async-handler.py
        │   ├── context-manager.py
        │   └── error-handling.py
        ├── javascript/
        │   └── promise-pattern.js
        └── markdown/
            └── decision-log.md
    """
    
    PATTERN_EXTENSIONS = {
        "python": ".py",
        "javascript": ".js",
        "typescript": ".ts",
        "rust": ".rs",
        "go": ".go",
        "java": ".java",
        "cpp": ".cpp",
        "c": ".c",
    }
    
    def __init__(self, patterns_dir: Optional[Path] = None):
        """
        Initialize the pattern library.
        
        Args:
            patterns_dir: Base directory for patterns. 
                         Defaults to ~/.hermes/brain/patterns/
        """
        if patterns_dir is None:
            brain_dir = Path.home() / ".hermes" / "brain"
            patterns_dir = brain_dir / "patterns"
        
        self.patterns_dir = Path(patterns_dir)
        self.patterns_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_category_dir(self, language: str) -> Path:
        """Get the directory for a language category."""
        category_dir = self.patterns_dir / language.lower()
        category_dir.mkdir(parents=True, exist_ok=True)
        return category_dir
    
    def _get_pattern_path(self, language: str, pattern_name: str) -> Path:
        """Get the file path for a pattern."""
        ext = self.PATTERN_EXTENSIONS.get(language.lower(), ".txt")
        # Sanitize pattern name
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in pattern_name)
        return self._get_category_dir(language) / f"{safe_name}{ext}"
    
    # === Pattern Storage ===
    
    def store_pattern(
        self,
        language: str,
        pattern_name: str,
        code: str,
        description: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Store a code pattern.
        
        Args:
            language: Programming language
            pattern_name: Unique name for the pattern
            code: The code pattern
            description: What this pattern does
            tags: Categorization tags
            metadata: Additional metadata
            
        Returns:
            Path to the stored pattern file
        """
        pattern_path = self._get_pattern_path(language, pattern_name)
        
        pattern_data = {
            "name": pattern_name,
            "language": language,
            "description": description,
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "code_hash": hashlib.sha256(code.encode()).hexdigest()[:16],
            "metadata": metadata or {},
            "code": code
        }
        
        with open(pattern_path, "w") as f:
            json.dump(pattern_data, f, indent=2)
        
        return pattern_path
    
    def load_pattern(self, language: str, pattern_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a specific pattern.
        
        Args:
            language: Programming language
            pattern_name: Name of the pattern
            
        Returns:
            Pattern data dict or None if not found
        """
        pattern_path = self._get_pattern_path(language, pattern_name)
        
        if not pattern_path.exists():
            return None
        
        with open(pattern_path, "r") as f:
            return json.load(f)
    
    def delete_pattern(self, language: str, pattern_name: str) -> bool:
        """
        Delete a pattern.
        
        Returns:
            True if deleted, False if not found
        """
        pattern_path = self._get_pattern_path(language, pattern_name)
        
        if pattern_path.exists():
            pattern_path.unlink()
            return True
        return False
    
    # === Pattern Discovery ===
    
    def list_patterns(
        self,
        language: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        List patterns, optionally filtered.
        
        Args:
            language: Filter by language
            tags: Filter by tags (AND logic)
            
        Returns:
            List of pattern metadata (without code content)
        """
        results = []
        
        if language:
            languages = [language.lower()]
        else:
            languages = [d.name for d in self.patterns_dir.iterdir() if d.is_dir()]
        
        for lang in languages:
            category_dir = self.patterns_dir / lang
            if not category_dir.is_dir():
                continue
            
            for pattern_file in category_dir.iterdir():
                if pattern_file.suffix not in self.PATTERN_EXTENSIONS.values():
                    continue
                
                try:
                    with open(pattern_file, "r") as f:
                        data = json.load(f)
                    
                    # Filter by tags if specified
                    if tags:
                        pattern_tags = set(data.get("tags", []))
                        if not all(t in pattern_tags for t in tags):
                            continue
                    
                    # Return metadata without code
                    metadata = {k: v for k, v in data.items() if k != "code"}
                    results.append(metadata)
                    
                except (json.JSONDecodeError, IOError):
                    continue
        
        return sorted(results, key=lambda x: x.get("created_at", ""), reverse=True)
    
    def find_similar_patterns(
        self,
        code_snippet: str,
        language: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find patterns similar to a code snippet.
        
        Uses simple hash-based matching for now.
        Can be enhanced with embeddings later.
        
        Args:
            code_snippet: Code to match against
            language: Programming language
            max_results: Maximum results to return
            
        Returns:
            List of similar patterns
        """
        snippet_hash = hashlib.sha256(code_snippet.encode()).hexdigest()[:16]
        
        patterns = self.list_patterns(language=language)
        matches = []
        
        for pattern in patterns:
            # Compare hash prefixes for rough similarity
            pattern_hash = pattern.get("code_hash", "")
            if pattern_hash[:8] == snippet_hash[:8]:
                matches.append(pattern)
                if len(matches) >= max_results:
                    break
        
        return matches
    
    # === Decision Log ===
    
    def log_decision(
        self,
        decision: str,
        context: str,
        rationale: str,
        alternatives: Optional[List[str]] = None
    ) -> Path:
        """
        Log a significant decision for future reference.
        
        Args:
            decision: What was decided
            context: Situation that required the decision
            rationale: Why this was the right choice
            alternatives: What alternatives were considered
            
        Returns:
            Path to the decision log
        """
        decision_log = self.patterns_dir / "markdown" / "decision-log.md"
        decision_log.parent.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().isoformat()
        decision_id = hashlib.md5(f"{timestamp}{decision}".encode()).hexdigest()[:8]
        
        entry = f"""
## [{decision_id}] {decision}

**Timestamp:** {timestamp}
**Context:** {context}
**Rationale:** {rationale}
{f"**Alternatives Considered:**\n" + "\n".join(f"- {a}" for a in alternatives) if alternatives else ""}

---
"""
        
        with open(decision_log, "a") as f:
            f.write(entry)
        
        return decision_log
    
    def get_recent_decisions(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        Get recent decisions from the decision log.
        
        Returns:
            List of decision dicts
        """
        decision_log = self.patterns_dir / "markdown" / "decision-log.md"
        
        if not decision_log.exists():
            return []
        
        decisions = []
        current = {}
        
        with open(decision_log, "r") as f:
            for line in f:
                line = line.strip()
                
                if line.startswith("## ["):
                    if current:
                        decisions.append(current)
                    # Parse: ## [id] title
                    parts = line[4:].split("] ", 1)
                    current = {"id": parts[0], "title": parts[1] if len(parts) > 1 else ""}
                elif line.startswith("**Timestamp:**"):
                    current["timestamp"] = line.split(":**", 1)[1].strip()
                elif line.startswith("**Context:**"):
                    current["context"] = line.split(":**", 1)[1].strip()
                elif line.startswith("**Rationale:**"):
                    current["rationale"] = line.split(":**", 1)[1].strip()
        
        if current:
            decisions.append(current)
        
        return decisions[-limit:]
    
    # === Import/Export ===
    
    def export_patterns(self, language: str, output_dir: Path) -> int:
        """
        Export all patterns for a language to a directory.
        
        Returns:
            Number of patterns exported
        """
        patterns = self.list_patterns(language=language)
        count = 0
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for pattern in patterns:
            pattern_data = self.load_pattern(language, pattern["name"])
            if pattern_data:
                output_path = output_dir / f"{pattern['name']}.json"
                with open(output_path, "w") as f:
                    json.dump(pattern_data, f, indent=2)
                count += 1
        
        return count
    
    def import_pattern(self, pattern_file: Path) -> Optional[Dict[str, Any]]:
        """
        Import a pattern from a JSON file.
        
        Returns:
            Imported pattern metadata or None on failure
        """
        try:
            with open(pattern_file, "r") as f:
                data = json.load(f)
            
            return self.store_pattern(
                language=data["language"],
                pattern_name=data["name"],
                code=data["code"],
                description=data.get("description", ""),
                tags=data.get("tags", []),
                metadata=data.get("metadata", {})
            )
        except (json.JSONDecodeError, KeyError) as e:
            return None
