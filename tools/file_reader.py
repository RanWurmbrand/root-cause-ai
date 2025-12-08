# file_reader.py
# Returns the FULL content of a file.
# If --out is provided, writes the output to a file.

import sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python file_reader.py /path/to/file [--out output.txt]")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    out_path = None

    if len(sys.argv) >= 4 and sys.argv[2] == "--out":
        out_path = Path(sys.argv[3]).resolve()

    if not file_path.is_file():
        msg = f"Invalid file: {file_path}"
        if out_path:
            out_path.write_text(msg, encoding="utf-8")
        else:
            print(msg)
        sys.exit(1)

    text = file_path.read_text(encoding="utf-8", errors="ignore")

    if out_path:
        out_path.write_text(text, encoding="utf-8")
    else:
        print(text)

if __name__ == "__main__":
    main()
