# code_applier.py
# Applies the suggested bug fix patch to the actual codebase

import json
import re
from pathlib import Path
from typing import List, Tuple, Optional


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
    
    def _parse_unified_diff(self, patch: str) -> Tuple[List[str], List[str]]:
        """
        Parse unified diff format into removed lines and added lines
        Returns: (lines_to_remove, lines_to_add)
        """
        removed = []
        added = []
        
        for line in patch.splitlines():
            # Skip metadata lines
            if line.startswith(("diff ", "index ", "@@", "---", "+++")):
                continue
            
            if line.startswith("+"):
                added.append(line[1:])  # Remove the '+' prefix
            elif line.startswith("-"):
                removed.append(line[1:])  # Remove the '-' prefix
            else:
                # Context lines (unchanged) appear in both
                removed.append(line)
                added.append(line)
        
        return removed, added
    
    def _find_and_replace_in_file(self, file_path: Path, old_lines: List[str], new_lines: List[str]) -> bool:
        """
        Find the old code block in the file and replace it with new code
        Returns True if successful, False otherwise
        """
        if not file_path.exists():
            print(f"[applier] File not found: {file_path}")
            return False
        
        content = file_path.read_text(encoding="utf-8")
        original_lines = content.splitlines()
        
        # Try to find the old code block
        old_block = "\n".join(old_lines).strip()
        new_block = "\n".join(new_lines).strip()
        
        if old_block in content:
            # Direct replacement
            new_content = content.replace(old_block, new_block)
            file_path.write_text(new_content, encoding="utf-8")
            return True
        
        # Try fuzzy matching with whitespace normalization
        old_normalized = re.sub(r'\s+', ' ', old_block).strip()
        
        for i in range(len(original_lines)):
            # Try to match starting from each line
            end_idx = min(i + len(old_lines) + 5, len(original_lines))
            candidate = "\n".join(original_lines[i:end_idx])
            candidate_normalized = re.sub(r'\s+', ' ', candidate).strip()
            
            if old_normalized in candidate_normalized:
                # Found a match - replace
                before = "\n".join(original_lines[:i])
                after = "\n".join(original_lines[end_idx:])
                new_content = before + "\n" + new_block + "\n" + after
                file_path.write_text(new_content, encoding="utf-8")
                return True
        
        print(f"[applier] Could not find old code block in {file_path}")
        return False
    
    def _extract_file_path_from_function_ref(self, func_ref: str) -> Optional[str]:
        """
        Extract file path from function reference like 'src/file.ts:functionName'
        Returns the file path part
        """
        if ":" in func_ref:
            return func_ref.split(":")[0]
        return None
    
    def apply_fix(self) -> dict:
        """
        Apply the latest fix to the codebase
        Returns a dict with success status and details
        """
        fix_path, fix_data = self._get_latest_fix()
        
        print(f"[applier] Using fix from: {fix_path}")
        
        functions_to_edit = fix_data.get("functions_to_edit", [])
        patch_suggestion = fix_data.get("patch_suggestion", "")
        reason = fix_data.get("reason", "")
        
        if not functions_to_edit:
            return {
                "success": False,
                "error": "No functions_to_edit specified in fix"
            }
        
        if not patch_suggestion:
            return {
                "success": False,
                "error": "No patch_suggestion provided in fix"
            }
        
        print(f"[applier] Reason: {reason}")
        print(f"[applier] Functions to edit: {functions_to_edit}")
        
        # Parse the patch
        removed_lines, added_lines = self._parse_unified_diff(patch_suggestion)
        
        # Determine which file to edit
        target_file = None
        for func_ref in functions_to_edit:
            file_path_str = self._extract_file_path_from_function_ref(func_ref)
            if file_path_str:
                target_file = Path(file_path_str)
                if not target_file.is_absolute():
                    target_file = (self.project_path / target_file).resolve()
                break
        
        if not target_file:
            return {
                "success": False,
                "error": f"Could not determine target file from: {functions_to_edit}"
            }
        
        print(f"[applier] Target file: {target_file}")
        
        # Apply the fix
        success = self._find_and_replace_in_file(target_file, removed_lines, added_lines)
        
        if success:
            print(f"[applier] ✓ Successfully applied fix to {target_file}")
            return {
                "success": True,
                "file": str(target_file),
                "functions": functions_to_edit,
                "reason": reason
            }
        else:
            return {
                "success": False,
                "error": f"Failed to apply fix to {target_file}"
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