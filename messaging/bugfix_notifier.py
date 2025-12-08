# bugfix_notifier.py
# Reads bug-fix result JSON + hint file, sends formatted message to Telegram.

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from messaging.telegram_manager import TelegramManager
from html import escape
load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
class BugFixMessageBuilder:
    def __init__(self):
        self.root = ROOT
        self.hints_dir = self.root / "artifacts" / "hints"
        self.fixes_dir = self.root / "artifacts" / "bug_fixes"

    def _get_latest(self, folder: Path, prefix: str) -> Path:
        files = sorted(folder.glob(f"{prefix}*.json"),
                       key=lambda p: p.stat().st_mtime,
                       reverse=True)
        if not files:
            raise RuntimeError(f"No files found in folder: {folder}")
        return files[0]

    def load_latest_hint(self) -> tuple[Path, dict]:
        path = self._get_latest(self.hints_dir, "hint_")
        data = json.loads(path.read_text(encoding="utf-8"))
        return path, data

    def load_latest_fix(self) -> tuple[Path, dict]:
        path = self._get_latest(self.fixes_dir, "fix_")
        data = json.loads(path.read_text(encoding="utf-8"))
        return path, data

    def build_message(self) -> str:
        # helper: split unified diff into "before" / "after"
        def split_patch(raw: str) -> tuple[str, str]:
            before_lines = []
            after_lines = []
            for line in raw.splitlines():
                # ignore metadata / headers
                if line.startswith(("diff ", "index ", "@@", "---", "+++")):
                    continue
                if line.startswith("+"):
                    after_lines.append(line[1:])
                elif line.startswith("-"):
                    before_lines.append(line[1:])
            before = "\n".join(before_lines).strip()
            after = "\n".join(after_lines).strip()
            return before, after

        # Extract values
        hint_path, hint_data = self.load_latest_hint()
        fix_path, fix_data = self.load_latest_fix()

        hint_first_line = str(hint_data.get("cause", "Unknown")).split("\n")[0]
        reason = fix_data.get("reason", "No reason provided.")
        functions = fix_data.get("functions_to_edit", [])

        # --- Build CURRENT vs SUGGESTED from a diff-like patch_suggestion ---
        raw_patch = (fix_data.get("patch_suggestion") or "").replace("```diff", "").replace("```", "").strip()
        lines = raw_patch.splitlines()

        current_lines: list[str] = []
        suggested_lines: list[str] = []

        for line in lines:
            if line.startswith("+"):
                # new-only line (appears only in suggested code)
                suggested_lines.append(line[1:])
            elif line.startswith("-"):
                # removed line (appears only in current code)
                current_lines.append(line[1:])
            else:
                # context / unchanged line → מופיע גם לפני וגם אחרי השינוי
                current_lines.append(line)
                suggested_lines.append(line)

        current_block = "\n".join(current_lines).strip()
        suggested_block = "\n".join(suggested_lines).strip()

        current_block = escape(current_block)
        suggested_block = escape(suggested_block)

        # Format function list
        fn_list = (
            "\n".join(f"• <code>{escape(f)}</code>" for f in functions)
            if functions else "<i>None</i>"
        )

        # Build HTML message
        msg = (
            "<b>🚨 Bug Fix Summary</b>\n\n"
            f"<b>🧩 Hint:</b>\n{escape(hint_first_line)}\n\n"
            f"<b>📂 Functions to Edit:</b>\n{fn_list}\n\n"
            f"<b>💡 Reason:</b>\n{escape(reason)}\n\n"
            f"<b>🧠 Patch Suggestion:</b>\n"
            f"<b>Current code:</b>\n<pre>{current_block or '(not available)'}</pre>\n\n"
            f"<b>Suggested fix:</b>\n<pre>{suggested_block}</pre>\n\n"
        )

        return msg

    
def main():
    builder = BugFixMessageBuilder()
    message = builder.build_message()
    tm = TelegramManager()
    tm.send_bugfix_message(message) 
    user_choice = tm.wait_for_user_response()
    print(user_choice)

if __name__ == "__main__":
    main()
