# project_tree_viewer.py
# Prints a clean project structure including files, excluding:
# 1) Hidden (starting with '.')
# 2) Entries from .gitignore (dirs only)
# 3) Common env/deps folders
# If --out FILE is given, writes output to FILE (overwrites).

import sys
from pathlib import Path

DEFAULT_EXCLUDES = {"node_modules", "venv", ".venv", "__pycache__", "env", "envs"}

def load_gitignore_excludes(project_path: Path):
    gi = project_path / ".gitignore"
    if not gi.is_file():
        return set()
    ex = set()
    for raw in gi.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.lstrip("/").rstrip("/")
        # ignore obvious file patterns
        if line.startswith("*") or ("." in Path(line).name and "/" not in line):
            continue
        if "/" in line:
            line = line.split("/")[0]
        ex.add(line)
    return ex

def build_tree(root: Path, excludes: set, prefix: str = "") -> list[str]:
    lines = []
    entries = sorted(list(root.iterdir()), key=lambda p: (not p.is_dir(), p.name.lower()))
    for idx, entry in enumerate(entries):
        name = entry.name
        if name.startswith(".") or name in excludes:
            continue
        connector = "└── " if idx == len(entries) - 1 else "├── "
        lines.append(f"{prefix}{connector}{name}")
        if entry.is_dir():
            new_prefix = prefix + ("    " if idx == len(entries) - 1 else "│   ")
            lines.extend(build_tree(entry, excludes, new_prefix))
    return lines

def main():
    if len(sys.argv) < 2:
        print("Usage: python project_tree_viewer.py /path/to/project [--out /path/to/file]")
        sys.exit(1)

    project_path = Path(sys.argv[1]).resolve()
    out_path = None
    if len(sys.argv) >= 4 and sys.argv[2] == "--out":
        out_path = Path(sys.argv[3]).resolve()

    if not project_path.is_dir():
        print(f"Invalid project path: {project_path}")
        sys.exit(1)

    excludes = DEFAULT_EXCLUDES | load_gitignore_excludes(project_path)
    output = [project_path.name] + build_tree(project_path, excludes)

    text = "\n".join(output)
    if out_path:
        out_path.write_text(text, encoding="utf-8")
    else:
        print(text)

if __name__ == "__main__":
    main()
