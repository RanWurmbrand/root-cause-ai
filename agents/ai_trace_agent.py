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

PROMPT_BASE = """You are a precise debugging assistant.
{tools_section}
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
{context_section}
"""

TOOLS_SECTION = """
You have access to one tool:
1) "read_output_log"
   - description: reads the VS Code extension output log (useful for deeper debugging)
   - use this ONLY if the terminal log doesn't have enough information
   - you can use this up to 3 times

If you need more context, return:
{{
  "action": "read_output_log"
}}

If you have enough information, return your analysis wrapped in:
{{
  "action": "final",
  "result": {{ ... your normal response here ... }}
}}
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
    def _extract_relevant_log(self, log_text: str, max_chars: int = 20000) -> str:
        lines = log_text.splitlines()
        error_keywords = ['error', 'fail', 'exception', 'traceback', 'assert']
        
        relevant = []
        for i, line in enumerate(lines):
            if any(kw in line.lower() for kw in error_keywords):
                start = max(0, i - 3)
                end = min(len(lines), i + 10)
                relevant.extend(lines[start:end])
        
        if not relevant:
            return log_text[-max_chars:]  # אם אין שגיאות, רק הסוף
        
        return "\n".join(relevant)[:max_chars]
    
    def _has_output_logs(self) -> bool:
        if os.getenv("COLLECT_OUTPUT_LOGS", "").lower() != "true":
            return False
        output_dir = ROOT / "artifacts" / "output_logs"
        if not output_dir.exists():
            return False
        return len(list(output_dir.glob("*.log"))) > 0
    

    def _build_prompt(self, log_text: str, context: dict) -> str:
        tools_section = TOOLS_SECTION if self._has_output_logs() else ""
        context_section = f"--- KNOWN CONTEXT ---\n{json.dumps(context, ensure_ascii=False)[:10000]}" if context else ""
        
        return PROMPT_BASE.format(
            tools_section=tools_section,
            log_text=log_text,
            context_section=context_section
        )
   
    def _read_output_log(self) -> str | None:
        output_dir = ROOT / "artifacts" / "output_logs"
        if not output_dir.exists():
            return None
        
        logs = sorted(
            output_dir.glob("*.log"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if not logs:
            return None
        
        content = logs[0].read_text(encoding="utf-8", errors="ignore")
        return self._extract_relevant_log(content)
    
    def analyze_log(self, log_text: str) -> tuple[AnalysisResult, int]:
        relevant_log = self._extract_relevant_log(log_text)
        has_tools = self._has_output_logs()
        context = {}
        total_tokens = 0
        output_log_reads = 0
        MAX_OUTPUT_LOG_READS = 3
        
        for step in range(1, 10):
            prompt = self._build_prompt(relevant_log, context)
            
            resp = self.model.generate_content(
                prompt,
                request_options={"timeout": 120}
            )
            
            if resp.usage_metadata:
                total_tokens += int(resp.usage_metadata.prompt_token_count)
                print(f"[trace-agent] Step {step} - Tokens: input={resp.usage_metadata.prompt_token_count}, output={resp.usage_metadata.candidates_token_count}")
            
            text = (resp.text or "").strip()
            
            if text.startswith("```"):
                text = text.strip("`")
                if text.lower().startswith("json"):
                    text = text[4:].strip()
            
            # אם אין כלים - פרסר ישיר כמו קודם
            if not has_tools:
                return self._parse_ai_response(text), total_tokens
            
            # אם יש כלים - בדוק אם זו בקשה לכלי או תשובה סופית
            try:
                msg = json.loads(text)
            except:
                print(f"[trace-agent] Non-JSON response, retrying...")
                continue
            
            action = msg.get("action", "")
            
            if action == "final":
                result_data = msg.get("result", {})
                return self._parse_ai_response(json.dumps(result_data)), total_tokens
            
            if action == "read_output_log":
                if output_log_reads >= MAX_OUTPUT_LOG_READS:
                    print(f"[trace-agent] Output log limit reached ({MAX_OUTPUT_LOG_READS})")
                    context["OUTPUT_LOG_LIMIT"] = "Limit reached"
                    continue
                
                output_log_reads += 1
                output_content = self._read_output_log()
                if output_content:
                    context["OUTPUT_LOG"] = output_content
                    print(f"[trace-agent] Read output log ({len(output_content)} chars)")
                else:
                    context["OUTPUT_LOG"] = "Not available"
                continue
            
            # אם אין action מוכר - נסה לפרסר כתשובה רגילה
            return self._parse_ai_response(text), total_tokens
    
        return AnalysisResult(cause="Could not analyze", hints=[]), total_tokens
    def answer_question(self, question: str) -> tuple[str, int]:
        """Receives a question from bug-fix agent and analyzes the log to answer"""
        latest_log = get_latest_log()
        log_text = latest_log.read_text(encoding="utf-8", errors="ignore")
        relevant_log = self._extract_relevant_log(log_text)
        
        prompt = f"""You are a debugging assistant. 
        A bug-fix agent is trying to fix an error and has a question about the logs.

        Answer the question based ONLY on the log content below.
        Be concise and specific. If the answer is not in the logs, say so.

        --- QUESTION ---
        {question}

        --- LOG ---
        {relevant_log}

        Answer in plain text, no JSON needed.
        """
        resp = self.model.generate_content(
            prompt,
            request_options={"timeout": 120}
        )
        
        input_tokens = 0
        if resp.usage_metadata:
            input_tokens = int(resp.usage_metadata.prompt_token_count)
            print(f"[trace-agent] Question answered - Tokens: input={resp.usage_metadata.prompt_token_count}, output={resp.usage_metadata.candidates_token_count}")
        
        answer = (resp.text or "").strip()
        return answer, input_tokens
    
    def run(self) -> Path:
        latest_log = get_latest_log()
        print(f"[trace-agent] Using latest log: {latest_log}")

        log_text = latest_log.read_text(encoding="utf-8", errors="ignore")
        result,input_tokens = self.analyze_log(log_text)

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
        return input_tokens


if __name__ == "__main__":
    agent = AiTraceAgent()
    agent.run()