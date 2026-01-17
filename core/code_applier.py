# code_applier.py
# Applies the suggested bug fix patch to the actual codebase

import json
import re
from pathlib import Path
from typing import List, Tuple, Optional
import subprocess


class CodeApplier:
    def __init__(self, project_path: str, root_path: Path):
        self.project_path = Path(project_path).resolve()
        self.root = root_path
        self.fixes_dir = self.root / "artifacts" / "bug_fixes"
        
        if not self.project_path.is_dir():
            raise ValueError(f"Invalid project path: {self.project_path}")
    
    def _get_latest_fix(self) -> Tuple[Path, dict]:
        """Get the most recent fix file"""
        fixes = sorted(
            self.fixes_dir.glob("fix_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if not fixes:
            raise RuntimeError(f"No fix files found in {self.fixes_dir}")
        
        fix_path = fixes[0]
        fix_data = json.loads(fix_path.read_text(encoding="utf-8"))
        return fix_path, fix_data

    def _resolve_file_path(self, file_path: str) -> Path:
        fpath = Path(file_path)
        
        if fpath.is_absolute() and fpath.exists():
            return fpath
        
        direct = (self.project_path / fpath).resolve()
        if direct.exists():
            return direct
        
        filename = fpath.name
        parent = fpath.parent.name if fpath.parent.name else None
        
        for found in self.project_path.rglob(filename):
            if parent is None or found.parent.name == parent:
                return found
        
        return direct

    def _parse_patch(self, raw_patch: str) -> List[Tuple[List[str], List[str]]]:
        """
        Parse patch into list of (old_lines, new_lines) hunks.
        Groups consecutive -/+ lines together.
        """
        # Clean up
        raw_patch = raw_patch.replace("```diff", "").replace("```", "").strip()
        lines = raw_patch.splitlines()
        
        hunks = []
        current_old = []
        current_new = []
        
        for line in lines:
            # Skip diff headers
            if line.startswith(("diff ", "index ", "@@", "---", "+++")):
                continue
            
            if line.startswith("-"):
                # If we had new lines without old, save that hunk first
                if current_new and not current_old:
                    hunks.append((current_old[:], current_new[:]))
                    current_old = []
                    current_new = []
                current_old.append(line[1:])
            elif line.startswith("+"):
                current_new.append(line[1:])
            else:
                # Context line or end of hunk - save current hunk if exists
                if current_old or current_new:
                    hunks.append((current_old[:], current_new[:]))
                    current_old = []
                    current_new = []
        
        # Don't forget last hunk
        if current_old or current_new:
            hunks.append((current_old, current_new))
        
        return hunks

    def _normalize(self, text: str) -> str:
        """Normalize whitespace for comparison"""
        return " ".join(text.split())

    def _find_and_replace(self, content: str, old_lines: List[str], new_lines: List[str]) -> Tuple[bool, str]:
        """
        Find old_lines block in content and replace with new_lines.
        Returns (success, new_content)
        """
        if not old_lines:
            # Pure addition - can't handle without context
            print(f"[applier] ⚠ Pure addition without context, skipping")
            return False, content
        
        file_lines = content.splitlines()
        
        # Try to find the block of old_lines
        old_normalized = [self._normalize(l) for l in old_lines]
        
        for start_idx in range(len(file_lines) - len(old_lines) + 1):
            match = True
            for j, old_line in enumerate(old_normalized):
                file_normalized = self._normalize(file_lines[start_idx + j])
                if file_normalized != old_line:
                    match = False
                    break
            
            if match:
                # Found it! Get the indentation from first matched line
                original_line = file_lines[start_idx]
                indent = len(original_line) - len(original_line.lstrip())
                
                # Apply indentation to new lines
                indented_new = []
                for new_line in new_lines:
                    if new_line.strip():
                        indented_new.append(" " * indent + new_line.strip())
                    else:
                        indented_new.append("")
                
                # Replace
                result_lines = file_lines[:start_idx] + indented_new + file_lines[start_idx + len(old_lines):]
                print(f"[applier] ✓ Replaced {len(old_lines)} line(s) at line {start_idx + 1}")
                return True, "\n".join(result_lines)
        
        # Fallback: try matching just the first old line
        if len(old_lines) == 1:
            old_norm = old_normalized[0]
            for i, file_line in enumerate(file_lines):
                if self._normalize(file_line) == old_norm:
                    indent = len(file_line) - len(file_line.lstrip())
                    new_content = " " * indent + new_lines[0].strip() if new_lines else ""
                    file_lines[i] = new_content
                    print(f"[applier] ✓ Replaced single line at {i + 1}")
                    return True, "\n".join(file_lines)
        
        print(f"[applier] ✗ Could not find: {old_lines[0][:50]}...")
        return False, content


    def apply_fix(self) -> dict:
        fix_path, fix_data = self._get_latest_fix()
        print(f"[applier] Using fix from: {fix_path}")
        
        # Extract data from new format
        functions_to_edit = fix_data.get("functions_to_edit", [])
        reason = fix_data.get("reason", "")
        raw_patch = fix_data.get("patch_suggestion", "")
        
        if not functions_to_edit:
            return {"success": False, "error": "No functions_to_edit specified"}
        
        if not raw_patch:
            return {"success": False, "error": "No patch_suggestion provided"}
        
        # Parse file path from first function (format: "file.ts:funcName")
        first_func = functions_to_edit[0]
        if ":" in first_func:
            file_path = first_func.rsplit(":", 1)[0]
        else:
            file_path = first_func
        
        target_file = self._resolve_file_path(file_path)
        print(f"[applier] Target file: {target_file}")
        print(f"[applier] Reason: {reason}")
        
        if not target_file.exists():
            return {"success": False, "error": f"File not found: {target_file}"}
        
        # Backup original
        original_content = target_file.read_text(encoding="utf-8")
        
        # Parse and apply hunks
        hunks = self._parse_patch(raw_patch)
        print(f"[applier] Found {len(hunks)} change hunk(s)")
        
        content = original_content
        applied_count = 0
        
        for i, (old_lines, new_lines) in enumerate(hunks):
            print(f"[applier] Applying hunk {i+1}: -{len(old_lines)} +{len(new_lines)} lines")
            success, content = self._find_and_replace(content, old_lines, new_lines)
            if success:
                applied_count += 1
        
        if applied_count == 0:
            return {"success": False, "error": "Could not apply any hunks"}
        
        # Write changes
        target_file.write_text(content, encoding="utf-8")
        
        # Validate syntax
        # if not self._validate_syntax(target_file):
        #     print(f"[applier] ✗ Syntax error after applying fix, reverting...")
        #     target_file.write_text(original_content, encoding="utf-8")
        #     return {"success": False, "error": "Applied fix created syntax error"}
        
        print(f"[applier] ✓ Successfully applied {applied_count}/{len(hunks)} hunk(s)")
        return {
            "success": True,
            "file": str(target_file),
            "function": functions_to_edit[0] if functions_to_edit else "",
            "reason": reason,
            "hunks_applied": applied_count
        }


if __name__ == "__main__":
    import sys
    
    if "--project" not in sys.argv:
        print("Usage: python code_applier.py --project /path/to/project")
        sys.exit(1)
    
    project_path = None
    for i, arg in enumerate(sys.argv):
        if arg == "--project" and i + 1 < len(sys.argv):
            project_path = sys.argv[i + 1]
    
    ROOT = Path(__file__).resolve().parents[1]
    applier = CodeApplier(project_path, ROOT)
    result = applier.apply_fix()
    
    print("\n" + "="*50)
    print(json.dumps(result, indent=2, ensure_ascii=False))