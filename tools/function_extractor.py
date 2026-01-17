# function_extractor.py
# Prints a function (Python/JS/TS/class method) if found.
# If --out FILE is given, writes the function to FILE (overwrites).

import sys
from pathlib import Path
import re

PATTERNS = [
    # Python
    lambda n: re.compile(rf"^\s*def\s+{re.escape(n)}\s*\("),
    # JS/TS named function
    lambda n: re.compile(rf"^\s*(export\s+)?(async\s+)?function\s+{re.escape(n)}\s*\("),
    # Arrow function assignment
    lambda n: re.compile(rf"^\s*(export\s+)?(const|let|var)\s+{re.escape(n)}\s*=\s*(async\s*)?\(.*\)\s*=>"),
    # TS class method (public/private/protected optional)
    lambda n: re.compile(rf"^\s*(public|private|protected)?\s*(async\s+)?{re.escape(n)}\s*\("),
]

def extract_function_text(lines: list[str], func_name: str) -> str | None:
    patterns = [p(func_name) for p in PATTERNS]
    start = None
    indent = None

    for i, line in enumerate(lines):
        if any(p.match(line) for p in patterns):
            start = i
            indent = len(line) - len(line.lstrip())
            break
    
    if start is None:
        return None

    # ספירת סוגריים מסולסלים
    brace_count = 0
    started = False
    buf = []
    
    for line in lines[start:]:
        buf.append(line)
        brace_count += line.count('{') - line.count('}')
        
        if brace_count > 0:
            started = True
        
        if started and brace_count == 0:
            break
    
    return "\n".join(buf).rstrip("\n")

def main():
    if len(sys.argv) < 3:
        print("Usage: python function_extractor.py /path/to/file function_name [--out /path/to/file]")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    func_name = sys.argv[2]
    out_path = None
    if len(sys.argv) >= 5 and sys.argv[3] == "--out":
        out_path = Path(sys.argv[4]).resolve()

    if not file_path.is_file():
        print(f"Invalid file: {file_path}")
        sys.exit(1)

    lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    text = extract_function_text(lines, func_name)
    if text is None:
        msg = f"Function '{func_name}' not found in {file_path}"
        if out_path:
            out_path.write_text(msg, encoding="utf-8")
        else:
            print(msg)
        sys.exit(0)

    if out_path:
        out_path.write_text(text, encoding="utf-8")
    else:
        print(text)

if __name__ == "__main__":
    main()
