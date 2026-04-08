"""
Hermes Coding MCP Server

A FastMCP server providing core file operations, code search, and command execution
for the Better Coder agent pipeline.
"""

import asyncio
import json
import os
import re
import subprocess
import threading
from pathlib import Path
from typing import Optional

try:
    from sdnotify import SystemdNotifier
    HAS_SDNOTIFY = True
except ImportError:
    HAS_SDNOTIFY = False

from mcp.server.fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP("hermes-coding-mcp")
_systemd_notifier = SystemdNotifier() if HAS_SDNOTIFY else None
_watchdog_stop = threading.Event()


# =============================================================================
# Tool 1: read_file
# =============================================================================

@mcp.tool()
async def read_file(
    path: str = Field(description="Absolute file path to read"),
    offset: Optional[int] = Field(default=1, ge=1, description="Line number to start reading from (1-indexed)"),
    limit: Optional[int] = Field(default=None, ge=1, description="Maximum number of lines to read"),
) -> str:
    """
    Read a file's contents with optional line range support.
    Returns JSON with path, content lines, total line count, and truncation flag.
    """
    try:
        file_path = Path(path)

        # Resolve symlinks to prevent path traversal via symlinks
        try:
            file_path = file_path.resolve()
        except (OSError, RuntimeError):
            return json.dumps({
                "isError": True,
                "error": "invalid_params",
                "message": f"Could not resolve path: {path}"
            })

        if not file_path.exists():
            return json.dumps({
                "isError": True,
                "error": "file_not_found",
                "message": f"File does not exist: {path}"
            })

        if not file_path.is_file():
            return json.dumps({
                "isError": True,
                "error": "invalid_params",
                "message": f"Path is not a file: {path}"
            })

        lines = file_path.read_text().splitlines()
        total_lines = len(lines)

        # Convert 1-indexed offset to 0-indexed
        start_idx = (offset - 1) if offset else 0

        if start_idx >= total_lines:
            return json.dumps({
                "isError": True,
                "error": "invalid_params",
                "message": f"Offset {offset} exceeds file length {total_lines}"
            })

        # Select lines
        end_idx = min(start_idx + (limit or total_lines), total_lines)
        selected_lines = lines[start_idx:end_idx]

        return json.dumps({
            "isError": False,
            "path": str(file_path.absolute()),
            "content": selected_lines,
            "total_lines": total_lines,
            "truncated": end_idx < total_lines,
            "offset": start_idx + 1,
            "limit": len(selected_lines)
        })

    except PermissionError:
        return json.dumps({
            "isError": True,
            "error": "permission_denied",
            "message": f"Permission denied reading: {path}"
        })
    except Exception as e:
        return json.dumps({
            "isError": True,
            "error": "unknown",
            "message": str(e)
        })


# =============================================================================
# Tool 2: write_file
# =============================================================================

@mcp.tool()
async def write_file(
    path: str = Field(description="Absolute file path to write"),
    content: str = Field(description="Content to write to the file"),
) -> str:
    """
    Write content to a file, creating it if it doesn't exist or overwriting if it does.
    Creates parent directories automatically if needed.
    Returns JSON with path, bytes written, and creation status.
    """
    try:
        file_path = Path(path)

        # Resolve symlinks and check for path traversal
        try:
            file_path = file_path.resolve()
        except (OSError, RuntimeError):
            return json.dumps({
                "isError": True,
                "error": "invalid_params",
                "message": f"Could not resolve path: {path}"
            })

        # Prevent path traversal - ensure path is under a reasonable root
        # Reject paths containing null bytes or that escape intended directories
        if '\x00' in path:
            return json.dumps({
                "isError": True,
                "error": "invalid_params",
                "message": "Path contains null bytes"
            })

        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if file exists
        created = not file_path.exists()

        # Write content
        bytes_written = file_path.write_text(content)

        return json.dumps({
            "isError": False,
            "path": str(file_path.absolute()),
            "bytes_written": bytes_written,
            "created": created,
            "overwritten": not created
        })

    except PermissionError:
        return json.dumps({
            "isError": True,
            "error": "permission_denied",
            "message": f"Permission denied writing: {path}"
        })
    except Exception as e:
        return json.dumps({
            "isError": True,
            "error": "unknown",
            "message": str(e)
        })


# =============================================================================
# Tool 3: search_code
# =============================================================================

@mcp.tool()
async def search_code(
    pattern: str = Field(description="Regex pattern to search for in file contents"),
    path: Optional[str] = Field(default=".", description="Directory or file path to search in"),
    file_glob: Optional[str] = Field(default=None, description="Glob pattern to filter files (e.g., '*.py', '*.js')"),
) -> str:
    """
    Search for a regex pattern in files within a directory.
    Returns matching lines with file paths and line numbers.
    Uses content output mode with line numbers by default.
    """
    try:
        # Validate regex pattern and check for potentially catastrophic patterns
        try:
            compiled = re.compile(pattern)
        except re.error as e:
            return json.dumps({
                "isError": True,
                "error": "invalid_params",
                "message": f"Invalid regex pattern: {e}"
            })

        # Check for patterns prone to catastrophic backtracking (ReDoS)
        # Patterns with nested quantifiers like (a+)+ or (a*)*
        dangerous_patterns = [
            r'(\w*)+', r'(\w+)+', r'(\w*)*', r'(\w+)*',
            r'([a-zA-Z]+)+', r'([a-zA-Z]*)*',
            r'(.+)+', r'(.*)*', r'(.)*', r'(.+)*',
            r'(\d+)+', r'(\d*)*',
        ]
        for dangerous in dangerous_patterns:
            if re.fullmatch(dangerous, pattern) or (dangerous in pattern and '+' in pattern[pattern.find(dangerous[1])+1:]):
                # Additional check: if pattern has nested quantifiers
                if _has_nested_quantifiers(pattern):
                    return json.dumps({
                        "isError": True,
                        "error": "invalid_params",
                        "message": "Regex pattern may cause catastrophic backtracking"
                    })

        search_path = Path(path)

        if not search_path.exists():
            return json.dumps({
                "isError": True,
                "error": "file_not_found",
                "message": f"Search path does not exist: {path}"
            })

        results = []
        max_results = 1000

        if search_path.is_file():
            # Search single file
            files_to_search = [search_path]
        else:
            # Search directory
            if file_glob:
                files_to_search = list(search_path.rglob(file_glob))
            else:
                files_to_search = list(search_path.rglob("*"))
            # Filter to only text files
            files_to_search = [f for f in files_to_search if f.is_file() and not _is_binary(f)]

        for file_path in files_to_search:
            if len(results) >= max_results:
                break

            try:
                content = file_path.read_text()
                lines = content.splitlines()

                for line_num, line in enumerate(lines, start=1):
                    if re.search(pattern, line):
                        results.append({
                            "path": str(file_path.absolute()),
                            "line": line_num,
                            "content": line
                        })
                        if len(results) >= max_results:
                            break
            except (PermissionError, UnicodeDecodeError):
                # Skip files we can't read
                continue

        return json.dumps({
            "isError": False,
            "pattern": pattern,
            "path": str(search_path.absolute()),
            "file_glob": file_glob,
            "matches": results,
            "match_count": len(results),
            "truncated": len(results) >= max_results
        })

    except PermissionError:
        return json.dumps({
            "isError": True,
            "error": "permission_denied",
            "message": f"Permission denied searching: {path}"
        })
    except Exception as e:
        return json.dumps({
            "isError": True,
            "error": "unknown",
            "message": str(e)
        })


def _is_binary(file_path: Path, chunk_size: int = 8192) -> bool:
    """Check if a file appears to be binary."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(chunk_size)
            # Check for null bytes or high proportion of non-printable chars
            if b'\x00' in chunk:
                return True
            # Check if mostly non-printable
            text_chars = bytes(range(32, 127)) + b'\n\r\t'
            non_text = sum(1 for byte in chunk if byte not in text_chars)
            if len(chunk) > 0 and non_text / len(chunk) > 0.3:
                return True
    except Exception:
        pass
    return False


def _has_nested_quantifiers(pattern: str) -> bool:
    """
    Detect nested quantifiers that can cause catastrophic backtracking.
    E.g., (a+)+, (a*)*, ([a-z]+)+ etc.
    """
    # Look for patterns like (something repeated)+ or (something repeated)*
    # Simple heuristic: check for patterns like ")++", ")+", ")*", "]*", etc.
    import re as re_module

    # Check for quantifier-followed-by-quantifier patterns
    nested_pattern = re_module.compile(r'[\+\*\?]\s*[\+\*\]')
    if nested_pattern.search(pattern):
        return True

    # Check for grouped quantifiers
    group_quantifier = re_module.compile(r'\([^)]*[\+\*\?][^)]*\)\s*[\+\*\?]')
    if group_quantifier.search(pattern):
        return True

    return False


# =============================================================================
# Tool 4: execute_command
# =============================================================================

@mcp.tool()
async def execute_command(
    command: str = Field(description="Shell command to execute"),
    timeout: Optional[int] = Field(default=180, ge=1, description="Maximum execution time in seconds (default: 180)"),
    workdir: Optional[str] = Field(default=None, description="Working directory for command execution"),
) -> str:
    """
    Execute a shell command and return its output.
    Returns JSON with exit code, stdout, stderr, and execution duration.
    """
    try:
        # Validate parameters
        if not command or not command.strip():
            return json.dumps({
                "isError": True,
                "error": "invalid_params",
                "message": "Command cannot be empty"
            })

        # Determine working directory
        cwd = workdir if workdir else os.getcwd()

        # Create subprocess
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )

        try:
            stdout_data, stderr_data = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            # Kill the process on timeout
            process.kill()
            await process.wait()
            return json.dumps({
                "isError": True,
                "error": "timeout",
                "message": f"Command timed out after {timeout} seconds",
                "command": command,
                "timeout": timeout
            })

        # Decode output, handling encoding issues gracefully
        try:
            stdout = stdout_data.decode('utf-8', errors='replace')
        except Exception:
            stdout = stdout_data.decode('latin-1', errors='replace')

        try:
            stderr = stderr_data.decode('utf-8', errors='replace')
        except Exception:
            stderr = stderr_data.decode('latin-1', errors='replace')

        return json.dumps({
            "isError": False,
            "command": command,
            "exit_code": process.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "timeout": timeout,
            "workdir": cwd
        })

    except PermissionError:
        return json.dumps({
            "isError": True,
            "error": "permission_denied",
            "message": f"Permission denied executing command"
        })
    except Exception as e:
        return json.dumps({
            "isError": True,
            "error": "unknown",
            "message": str(e)
        })


# =============================================================================
# Health Check Tool
# =============================================================================

@mcp.tool()
async def health_check() -> str:
    """
    Health check endpoint for systemd watchdog and monitoring.
    Returns healthy status with list of available tools.
    """
    return json.dumps({
        "status": "ok",
        "tools": ["read_file", "write_file", "search_code", "execute_command", "health_check"]
    })


# =============================================================================
# Watchdog Notification Thread
# =============================================================================

def _watchdog_loop():
    """Background thread to ping systemd watchdog every 15 seconds."""
    import time
    while not _watchdog_stop.wait(15):
        try:
            if HAS_SDNOTIFY and _systemd_notifier:
                _systemd_notifier.notify("WATCHDOG=1")
        except Exception:
            pass


def _start_watchdog():
    """Start the watchdog notification thread."""
    if HAS_SDNOTIFY:
        t = threading.Thread(target=_watchdog_loop, daemon=True)
        t.start()
        return t
    return None


# =============================================================================
# Server Entry Point
# =============================================================================

if __name__ == "__main__":
    # Start watchdog thread for systemd
    watchdog_thread = _start_watchdog()

    # Signal systemd that service is ready (only if sdnotify is available)
    if HAS_SDNOTIFY and _systemd_notifier:
        try:
            _systemd_notifier.notify("READY=1")
        except Exception:
            pass

    try:
        mcp.run()
    finally:
        # Signal watchdog to stop
        _watchdog_stop.set()
        if watchdog_thread:
            watchdog_thread.join(timeout=5)
