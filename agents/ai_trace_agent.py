# ai_trace_agent.py
# AI-only: reads a test log file, sends it to Gemini (GEMINI_API_KEY),
# expects strict JSON with "cause" and "hints", then prints to stdout.

import os
import sys
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import time

from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
except ImportError:
    print("Missing dependency: google-generativeai", file=sys.stderr)
    sys.exit(1)

MODEL_NAME = "models/gemini-2.5-flash"
ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "artifacts" / "rootcause_logs"

def get_latest_log() -> Path:
    if not LOG_DIR.exists():
        print(f"No log directory found: {LOG_DIR}")
        sys.exit(1)

    logs = sorted(
        LOG_DIR.glob("*.log"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if not logs:
        print("No log files found in rootcause_logs/")
        sys.exit(1)

    return logs[0]

@dataclass
class Hint:
    description: str
    file: Optional[str] = None
    function: Optional[str] = None
    line: Optional[int] = None

@dataclass
class AnalysisResult:
    cause: str
    hints: List[Hint]

PROMPT_TEMPLATE = """You are a precise debugging assistant.
Given ONLY the test log below, return STRICT JSON with:
The "file" field inside each hint is **mandatory**. 
Never leave it null. If you are not "100%" sure, guess the most likely file name 
based on the log content or stack trace.

1) "cause": one short, informative sentence (max ~20 words) explaining why the error happened.
2) "hints": an array of objects; each has:
   - "description": concise, actionable description of what caused the error and where
   - "file": absolute or relative file path,
   - "function": function name if known, else null
   - "line": integer line number if known, else null


DO NOT add extra keys. DO NOT wrap in code fences. Return ONLY valid JSON.

IMPORTANT:
- If multiple errors appear to be caused by one root issue, return only ONE consolidated hint.
- You may mention that other errors are cascading from the root cause, but DO NOT list or count them.
- Do not output numbers of errors or hints (e.g., “5 errors”, “3 hints”) — only a single root-cause hint.

--- LOG START ---
{log_text}
--- LOG END ---
"""

class AiTraceAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing GEMINI_API_KEY")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(MODEL_NAME)

        self.hints_dir = ROOT / "artifacts" / "hints"
        self.hints_dir.mkdir(exist_ok=True)

    def _parse_ai_response(self, text: str) -> AnalysisResult:
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()

        data = json.loads(text)

        cause = str(data.get("cause", "")).strip()
        low = cause.lower()

        # Clean log → no errors
        if (
            "no errors" in low or
            "all tests passed" in low or
            "passed successfully" in low or
            "0 failed" in low
        ):
            return AnalysisResult(
                cause="[trace-agent] CLEAN",
                hints=[]
            )

        hints_raw = data.get("hints") or []
        hints: List[Hint] = []

        for h in hints_raw:
            line_val = h.get("line")
            if isinstance(line_val, str) and line_val.isdigit():
                line_val = int(line_val)
            elif not isinstance(line_val, int):
                line_val = None

            hints.append(Hint(
                description=str(h.get("description") or "").strip(),
                file=h.get("file") or None,
                function=h.get("function") or None,
                line=line_val
            ))

        return AnalysisResult(cause=cause, hints=hints)

    def analyze_log(self, log_text: str) -> AnalysisResult:
        prompt = PROMPT_TEMPLATE.format(log_text=log_text[:20000])
        resp = self.model.generate_content(prompt)
        text = (resp.text or "").strip()
        return self._parse_ai_response(text)

    def run(self) -> Path:
        latest_log = get_latest_log()
        print(f"[trace-agent] Using latest log: {latest_log}")

        log_text = latest_log.read_text(encoding="utf-8", errors="ignore")
        result = self.analyze_log(log_text)

        import time
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        out_file = self.hints_dir / f"hint_{timestamp}.json"

        referenced_path = None
        if result.hints and result.hints[0].file:
            referenced_path = result.hints[0].file

        out_file.write_text(
            json.dumps({
                "path": referenced_path,
                "cause": result.cause,
                "hints": [h.__dict__ for h in result.hints]
            }, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        print(f"[trace-agent] Wrote hint to: {out_file}")
        return out_file


if __name__ == "__main__":
    agent = AiTraceAgent()
    agent.run()