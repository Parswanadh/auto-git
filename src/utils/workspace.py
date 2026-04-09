"""
Workspace — Directory-aware project scanner & editor.

Gives auto-git Claude-Code-like awareness of the current working directory:
  • Builds a hierarchical file tree
  • Reads / writes / patches individual files
  • Generates a compact repo map (path + exports) for LLM context
  • Detects project type (Python, Node, Rust, …) and entrypoints
"""

from __future__ import annotations

import ast
import fnmatch
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ── Ignore patterns (similar to .gitignore defaults) ────────────────────
DEFAULT_IGNORE = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    "*.egg-info",
    ".eggs",
    ".next",
    ".nuxt",
    ".DS_Store",
    "Thumbs.db",
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.dylib",
    "*.dll",
    "*.o",
    "*.obj",
    "*.class",
    "*.jar",
}

# Extensions we consider "text" files worth reading
TEXT_EXTENSIONS = {
    ".py", ".pyi", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs",
    ".rs", ".go", ".java", ".kt", ".c", ".cpp", ".h", ".hpp",
    ".cs", ".rb", ".php", ".swift", ".scala", ".lua",
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".md", ".rst", ".txt", ".csv",
    ".sh", ".bash", ".zsh", ".fish", ".bat", ".cmd", ".ps1",
    ".sql", ".graphql", ".proto",
    ".dockerfile", ".env", ".gitignore", ".editorconfig",
    ".xml", ".svg",
}

# Max file size we'll read into memory (256 KB)
MAX_FILE_SIZE = 256 * 1024


# ── Data classes ────────────────────────────────────────────────────────

@dataclass
class FileInfo:
    """Metadata about a single file."""
    path: str           # Relative to workspace root
    abs_path: str       # Absolute path
    size: int           # Bytes
    extension: str
    is_text: bool
    lines: int = 0
    exports: List[str] = field(default_factory=list)  # Top-level symbols


@dataclass
class ProjectInfo:
    """Detected project metadata."""
    root: str
    project_type: str           # python, node, rust, go, java, unknown
    entrypoints: List[str]      # e.g. main.py, index.js
    config_files: List[str]     # e.g. pyproject.toml, package.json
    dependency_file: str = ""   # e.g. requirements.txt, package.json
    language: str = ""


@dataclass
class Workspace:
    """
    Represents a scanned workspace directory.
    Use ``scan()`` to create one, then query files / generate maps.
    """
    root: Path
    files: Dict[str, FileInfo] = field(default_factory=dict)
    tree_text: str = ""
    project: Optional[ProjectInfo] = None

    # ─── Scanning ───────────────────────────────────────────────────

    @classmethod
    def scan(
        cls,
        root: str | Path,
        *,
        max_files: int = 5000,
        extra_ignore: Set[str] | None = None,
        gitignore: bool = True,
    ) -> "Workspace":
        """
        Walk *root* and catalogue every text file.

        Returns a populated ``Workspace`` instance.
        """
        root = Path(root).resolve()
        ignore = set(DEFAULT_IGNORE)
        if extra_ignore:
            ignore |= extra_ignore

        # Parse .gitignore if present
        gitignore_patterns: List[str] = []
        if gitignore:
            gi = root / ".gitignore"
            if gi.is_file():
                gitignore_patterns = _parse_gitignore(gi)

        ws = cls(root=root)
        count = 0

        for dirpath, dirnames, filenames in os.walk(root, topdown=True):
            # Prune ignored directories in-place
            rel_dir = os.path.relpath(dirpath, root)
            dirnames[:] = [
                d for d in dirnames
                if not _should_ignore(d, rel_dir, ignore, gitignore_patterns)
            ]

            for fname in filenames:
                if count >= max_files:
                    break
                if _should_ignore(fname, rel_dir, ignore, gitignore_patterns):
                    continue

                abs_p = os.path.join(dirpath, fname)
                rel_p = os.path.relpath(abs_p, root).replace("\\", "/")
                ext = os.path.splitext(fname)[1].lower()
                is_text = ext in TEXT_EXTENSIONS or fname in (
                    "Makefile", "Dockerfile", "Procfile", "Pipfile",
                    "Gemfile", "Rakefile", "Justfile",
                )

                try:
                    size = os.path.getsize(abs_p)
                except OSError:
                    continue

                fi = FileInfo(
                    path=rel_p,
                    abs_path=abs_p,
                    size=size,
                    extension=ext,
                    is_text=is_text,
                )

                if is_text and size <= MAX_FILE_SIZE:
                    try:
                        content = Path(abs_p).read_text(encoding="utf-8", errors="replace")
                        fi.lines = content.count("\n") + 1
                        if ext == ".py":
                            fi.exports = _extract_python_exports(content)
                    except Exception:
                        pass

                ws.files[rel_p] = fi
                count += 1

            if count >= max_files:
                break

        ws.tree_text = ws._build_tree()
        ws.project = ws._detect_project()
        return ws

    # ─── File operations ────────────────────────────────────────────

    def read_file(self, rel_path: str) -> Optional[str]:
        """Read a file's contents. Returns None if not found or binary."""
        fi = self.files.get(rel_path)
        if fi is None:
            # Try direct read
            abs_p = self.root / rel_path
            if not abs_p.is_file():
                return None
            fi = FileInfo(
                path=rel_path,
                abs_path=str(abs_p),
                size=abs_p.stat().st_size,
                extension=abs_p.suffix.lower(),
                is_text=True,
            )

        if not fi.is_text or fi.size > MAX_FILE_SIZE:
            return None

        try:
            return Path(fi.abs_path).read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

    def write_file(self, rel_path: str, content: str) -> bool:
        """Write content to a file (creates parent dirs as needed)."""
        abs_p = self.root / rel_path
        try:
            abs_p.parent.mkdir(parents=True, exist_ok=True)
            abs_p.write_text(content, encoding="utf-8")
            # Update index
            self.files[rel_path] = FileInfo(
                path=rel_path,
                abs_path=str(abs_p),
                size=len(content.encode("utf-8")),
                extension=abs_p.suffix.lower(),
                is_text=True,
                lines=content.count("\n") + 1,
                exports=_extract_python_exports(content) if abs_p.suffix == ".py" else [],
            )
            return True
        except Exception:
            return False

    def patch_file(self, rel_path: str, old: str, new: str) -> bool:
        """Replace exactly one occurrence of *old* with *new* in a file."""
        content = self.read_file(rel_path)
        if content is None:
            return False
        if content.count(old) != 1:
            return False
        updated = content.replace(old, new, 1)
        return self.write_file(rel_path, updated)

    def delete_file(self, rel_path: str) -> bool:
        """Delete a file from the workspace."""
        abs_p = self.root / rel_path
        try:
            abs_p.unlink()
            self.files.pop(rel_path, None)
            return True
        except Exception:
            return False

    # ─── Queries ────────────────────────────────────────────────────

    def list_files(
        self,
        pattern: str = "*",
        text_only: bool = True,
    ) -> List[str]:
        """Return relative paths matching a glob-like pattern."""
        result = []
        for rel in sorted(self.files):
            fi = self.files[rel]
            if text_only and not fi.is_text:
                continue
            if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(os.path.basename(rel), pattern):
                result.append(rel)
        return result

    def search_content(self, query: str, *, max_results: int = 50) -> List[Tuple[str, int, str]]:
        """
        Grep-like search across all text files.
        Returns list of (file, line_number, line_text).
        """
        results = []
        try:
            pat = re.compile(query, re.IGNORECASE)
        except re.error:
            pat = re.compile(re.escape(query), re.IGNORECASE)

        for rel in sorted(self.files):
            fi = self.files[rel]
            if not fi.is_text or fi.size > MAX_FILE_SIZE:
                continue
            content = self.read_file(rel)
            if content is None:
                continue
            for i, line in enumerate(content.splitlines(), 1):
                if pat.search(line):
                    results.append((rel, i, line.rstrip()))
                    if len(results) >= max_results:
                        return results
        return results

    def get_summary(self) -> Dict:
        """Return a compact dict summarising the workspace."""
        ext_counts: Dict[str, int] = {}
        total_lines = 0
        for fi in self.files.values():
            ext_counts[fi.extension] = ext_counts.get(fi.extension, 0) + 1
            total_lines += fi.lines
        return {
            "root": str(self.root),
            "total_files": len(self.files),
            "total_lines": total_lines,
            "extensions": dict(sorted(ext_counts.items(), key=lambda x: -x[1])),
            "project_type": self.project.project_type if self.project else "unknown",
            "entrypoints": self.project.entrypoints if self.project else [],
        }

    # ─── Repo map (for LLM context) ────────────────────────────────

    def build_repo_map(self, *, max_tokens: int = 4000, focus_query: str = "") -> str:
        """
        Build a compact repo map suitable for LLM prompts.

        Format:
            path/file.py  (42 lines)
              class Foo
              def bar()
              def baz()
        """
        lines: List[str] = []
        char_budget = max_tokens * 4  # rough chars→tokens

        # Rank files for prompt relevance (focus terms + structural centrality).
        focus_terms = {
            t.lower()
            for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", focus_query or "")
        }
        entrypoints = set(self.project.entrypoints if self.project else [])

        py_stem_to_path: Dict[str, str] = {}
        for rel in self.files:
            if rel.endswith(".py"):
                py_stem_to_path[Path(rel).stem] = rel

        inbound_refs: Dict[str, int] = {rel: 0 for rel in self.files}
        for rel, fi in self.files.items():
            if not rel.endswith(".py") or not fi.is_text or fi.size > MAX_FILE_SIZE:
                continue
            content = self.read_file(rel)
            if not content:
                continue
            for imported_mod in _extract_python_imports(content):
                imported_stem = imported_mod.split(".")[0]
                target = py_stem_to_path.get(imported_stem)
                if target and target != rel:
                    inbound_refs[target] = inbound_refs.get(target, 0) + 1

        def _score(rel: str, fi: FileInfo) -> int:
            score = 0
            if fi.extension in {".py", ".pyi"}:
                score += 10
            elif fi.extension in {".yaml", ".yml", ".toml", ".json", ".cfg", ".ini"}:
                score += 6
            elif fi.extension in {".md", ".rst"}:
                score += 3

            if rel in entrypoints:
                score += 18

            score += min(inbound_refs.get(rel, 0), 20) * 2

            if focus_terms:
                searchable = " ".join([rel] + fi.exports).lower()
                overlap = sum(1 for term in focus_terms if term in searchable)
                score += overlap * 7

            if fi.exports:
                score += min(len(fi.exports), 8)

            # Smaller files are usually better context snippets than huge blobs.
            if 0 < fi.lines <= 400:
                score += 2
            return score

        ranked = sorted(
            ((rel, self.files[rel]) for rel in self.files if self.files[rel].is_text),
            key=lambda item: (-_score(item[0], item[1]), item[0]),
        )

        included_files = 0
        for rel, fi in ranked:
            entry = f"{rel}  ({fi.lines} lines)"
            if fi.exports:
                entry += "\n" + "\n".join(f"  {e}" for e in fi.exports[:20])

            projected_size = sum(len(l) for l in lines) + len(entry)
            if projected_size > char_budget:
                remaining = max(len(ranked) - included_files, 0)
                lines.append(f"... and {remaining} more files")
                break

            lines.append(entry)
            included_files += 1

        return "\n".join(lines)

    def build_full_context(self, *, max_chars: int = 120_000) -> str:
        """
        Build full file contents for LLM context (for refine mode).
        Prioritises Python, config, then others. Truncates if too large.
        """
        # Priority ordering
        def _priority(rel: str) -> int:
            if rel.endswith((".py", ".pyi")):
                return 0
            if rel.endswith((".yaml", ".yml", ".toml", ".json", ".cfg")):
                return 1
            if rel.endswith((".md", ".rst", ".txt")):
                return 2
            return 3

        ordered = sorted(self.files.keys(), key=lambda r: (_priority(r), r))

        sections: List[str] = []
        used = 0
        for rel in ordered:
            fi = self.files[rel]
            if not fi.is_text or fi.size > MAX_FILE_SIZE:
                continue
            content = self.read_file(rel)
            if content is None:
                continue
            block = f"═══ {rel} ({fi.lines} lines) ═══\n{content}\n"
            if used + len(block) > max_chars:
                remaining = len(ordered) - len(sections)
                sections.append(f"\n... {remaining} more files omitted (context limit)\n")
                break
            sections.append(block)
            used += len(block)

        return "\n".join(sections)

    # ─── Internal helpers ───────────────────────────────────────────

    def _build_tree(self, *, indent: int = 2) -> str:
        """Build a text tree like `tree` command output."""
        dirs: Dict[str, List[str]] = {}
        for rel in sorted(self.files):
            parent = os.path.dirname(rel) or "."
            dirs.setdefault(parent, []).append(os.path.basename(rel))

        lines = [f"{self.root.name}/"]
        _tree_recurse(lines, dirs, ".", prefix="", indent=indent)
        return "\n".join(lines)

    def _detect_project(self) -> ProjectInfo:
        """Detect project type, entrypoints, and config files."""
        info = ProjectInfo(root=str(self.root), project_type="unknown", entrypoints=[], config_files=[])

        markers = {
            "pyproject.toml": "python",
            "setup.py": "python",
            "setup.cfg": "python",
            "requirements.txt": "python",
            "Pipfile": "python",
            "package.json": "node",
            "tsconfig.json": "node",
            "Cargo.toml": "rust",
            "go.mod": "go",
            "pom.xml": "java",
            "build.gradle": "java",
        }

        # Count votes per language from detected markers (root-level only)
        type_votes: Dict[str, int] = {}
        for rel in self.files:
            base = os.path.basename(rel)
            if base in markers:
                lang = markers[base]
                # Root-level markers get more weight
                depth = rel.count("/")
                weight = 3 if depth == 0 else 1
                type_votes[lang] = type_votes.get(lang, 0) + weight
                info.config_files.append(rel)

        # Also weight by file count (dominant language gets strong signal)
        lang_files = {
            "python": sum(1 for f in self.files if f.endswith(".py")),
            "node": sum(1 for f in self.files if f.endswith((".js", ".ts", ".jsx", ".tsx"))),
            "rust": sum(1 for f in self.files if f.endswith(".rs")),
            "go": sum(1 for f in self.files if f.endswith(".go")),
        }
        if lang_files:
            dominant = max(lang_files, key=lang_files.get)
            for lang, count in lang_files.items():
                if count > 10:
                    bonus = 5 if lang == dominant else 2
                    type_votes[lang] = type_votes.get(lang, 0) + bonus

        if type_votes:
            info.project_type = max(type_votes, key=type_votes.get)

        # Entrypoints
        entry_names = {
            "python": ["main.py", "app.py", "cli.py", "__main__.py", "run.py", "manage.py", "cli_entry.py"],
            "node": ["index.js", "index.ts", "app.js", "app.ts", "server.js", "server.ts"],
            "rust": ["src/main.rs", "src/lib.rs"],
            "go": ["main.go", "cmd/main.go"],
            "java": ["src/main/java/Main.java"],
        }
        for name in entry_names.get(info.project_type, []):
            if name in self.files:
                info.entrypoints.append(name)

        # Fallback: for Python projects, find root-level scripts with if __name__
        if info.project_type == "python" and not info.entrypoints:
            for rel, fi in self.files.items():
                if "/" not in rel and fi.extension == ".py" and fi.is_text:
                    try:
                        content = Path(fi.abs_path).read_text(encoding="utf-8", errors="replace")
                        if "__name__" in content and "__main__" in content:
                            info.entrypoints.append(rel)
                            if len(info.entrypoints) >= 3:
                                break
                    except Exception:
                        pass

        # Dependency file
        dep_files = {
            "python": ["requirements.txt", "pyproject.toml", "Pipfile"],
            "node": ["package.json"],
            "rust": ["Cargo.toml"],
            "go": ["go.mod"],
        }
        for dep in dep_files.get(info.project_type, []):
            if dep in self.files:
                info.dependency_file = dep
                break

        info.language = info.project_type
        return info


# ── Module-level helpers ────────────────────────────────────────────────

def _should_ignore(
    name: str,
    rel_dir: str,
    ignore_set: Set[str],
    gitignore_patterns: List[str],
) -> bool:
    """Check if a file/directory name should be skipped."""
    # Direct match
    if name in ignore_set:
        return True
    # Glob match
    for pat in ignore_set:
        if fnmatch.fnmatch(name, pat):
            return True
    # .gitignore patterns
    rel_path = f"{rel_dir}/{name}".replace("\\", "/").lstrip("./")
    for pat in gitignore_patterns:
        if fnmatch.fnmatch(rel_path, pat) or fnmatch.fnmatch(name, pat):
            return True
    return False


def _parse_gitignore(path: Path) -> List[str]:
    """Parse a .gitignore file into a list of fnmatch patterns."""
    patterns = []
    try:
        for line in path.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Negate patterns not supported (complex), skip them
            if line.startswith("!"):
                continue
            # Convert git patterns to fnmatch-compatible
            # Strip trailing /
            if line.endswith("/"):
                line = line[:-1]
            patterns.append(line)
    except Exception:
        pass
    return patterns


def _extract_python_exports(code: str) -> List[str]:
    """Extract top-level class/function names from Python source."""
    exports = []
    try:
        tree = ast.parse(code)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                exports.append(f"class {node.name}")
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                exports.append(f"def {node.name}()")
    except SyntaxError:
        # Fallback regex for files with syntax errors
        for m in re.finditer(r"^(?:class|def|async\s+def)\s+(\w+)", code, re.MULTILINE):
            exports.append(m.group(0))
    return exports


def _extract_python_imports(code: str) -> List[str]:
    """Extract imported module paths from Python source."""
    modules: List[str] = []
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name:
                        modules.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    modules.append(node.module)
    except SyntaxError:
        # Best-effort fallback for syntactically invalid files.
        for m in re.finditer(r"^\s*import\s+([A-Za-z0-9_\.]+)", code, re.MULTILINE):
            modules.append(m.group(1))
        for m in re.finditer(r"^\s*from\s+([A-Za-z0-9_\.]+)\s+import\s+", code, re.MULTILINE):
            modules.append(m.group(1))
    return modules


def _tree_recurse(
    lines: List[str],
    dirs: Dict[str, List[str]],
    current: str,
    prefix: str,
    indent: int,
) -> None:
    """Recursive helper for _build_tree."""
    files_here = dirs.get(current, [])
    # Collect sub-directories that have files
    sub_dirs = sorted(
        d for d in dirs
        if d != current and (os.path.dirname(d) or ".") == current
    )

    entries = sub_dirs + files_here
    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        if entry in sub_dirs:
            lines.append(f"{prefix}{connector}{os.path.basename(entry)}/")
            extension = "    " if is_last else "│   "
            _tree_recurse(lines, dirs, entry, prefix + extension, indent)
        else:
            lines.append(f"{prefix}{connector}{entry}")
