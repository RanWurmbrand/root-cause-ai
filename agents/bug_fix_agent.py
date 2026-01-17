# bug_fix_agent.py
# Agentic bug-fix suggester that:
# 1) Reads a HINT from --hint (default: tmphint.txt)
# 2) Lets the AI decide which local tools to run (project_tree_viewer.py, function_extractor.py)
# 3) Runs requested tools, feeds results back to the AI
# 4) Prints intermediate tool runs AND a final JSON with the minimal patch suggestion

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any
import time
from dotenv import load_dotenv
import re
load_dotenv()
from agents.ai_trace_agent import AiTraceAgent
ROOT = Path(__file__).resolve().parents[1]
trace_questions = 0
MAX_TRACE_QUESTIONS = 3
# ---- Gemini client ----
try:
    import google.generativeai as genai
except ImportError:
    print("Missing dependency: google-generativeai", file=sys.stderr)
    sys.exit(1)

LOG_DIR = ROOT / "rootcause_logs"
MODEL_NAME = "models/gemini-2.5-flash"

CONTROLLER_PROMPT = """You are an autonomous debugging agent. You have ONLY a short human hint.
You can ask the controller to run LOCAL TOOLS for you, and you will receive their outputs:

CRITICAL RULES:
- NEVER suggest fixes to files inside node_modules/ or any dependency folder
- NEVER suggest fixes to third-party libraries
- The bug is ALWAYS in the project's own code, not in dependencies
- If the error originates from a dependency, find the PROJECT code that calls it incorrectly
- Look for configuration files, test setup, or initialization code that might 

Available tools you can request with an "action":
1) "run_tree"
   - description: prints the project structure (dirs+files), excluding hidden/.gitignored/common env dirs
   - params: none
   - output label: "PROJECT_TREE"
2) "extract_function"
   - description: print a function by name from a specific file
   - params:
       "file_path": string
       "function_name": string  ← MUST be provided
   - IMPORTANT: never call extract_function without function_name.
   - output label: "FUNCTION::<file>::<func>"
3) "read_file"
   - description: returns the FULL content of a file.
   - WARNING: This tool is extremely expensive. Use it ONLY if no function_name can be inferred.
   - params:
       "file_path": string (absolute or project-relative)
   - output label: "FILE::<path>"
4) "ask_trace_agent"
   - description: ask the trace agent a question about the error logs. Use this when you need more details about the error that are not in the hint.
   - WARNING: This tool is VERY expensive. Use it ONLY as a last resort when you cannot understand the error from the hint and other tools.
   - params:
       "question": string (your question about the logs)
   - you can use this up to 3 times
   - output label: "TRACE_ANSWER"

Goal:
- Propose a MINIMAL fix that changes as little logic as possible.
- List which function(s) should be edited.
- Provide a short reason.
- Provide a MINIMAL patch with ONLY the lines that change:
  - removed lines start with "-"
  - added lines start with "+"
  - do NOT include context lines (unchanged lines)
  - do NOT include file headers
  - no code fences
  - Example: if changing one line, return only 2 lines (one "-" and one "+")

Loop:
- If you need more context, return an action to run a tool with the correct params.
- If you have enough information, return "final" with the result.

STRICT JSON ONLY for EVERY step.

Schema for a non-final step:
{{
  "action": "run_tree" | "extract_function",
  "params": {{ ... }}
}}

For extract_function:
{{
  "action": "extract_function",
  "params": {{ "file_path": "path/to/file.ts", "function_name": "myFunc" }}
}}

Schema for final step:
{{
  "action": "final",
  "result": {{
    "functions_to_edit": ["file.ts:funcName", ...],
    "reason": "one short informative sentence",
    "patch_suggestion": "a small unified diff hunk (only +/- lines, no headers, no code fences, minimal change)"
  }}
}}

Now your inputs:

--- HINT ---
{hint}

--- KNOWN CONTEXT (controller accumulates tool outputs for you) ---
{context}
Additional rule:
- If multiple failures exist but clearly originate from a single root issue, treat them as one problem.
- You may state that other failures are cascading from the same source, but DO NOT enumerate or count them.
- Do not reference quantities like "x errors" or "y hints".

"""

class BugFixAgent:
    
    def __init__(self, project_path: str, user_feedback: str = None):
        self.project_path = Path(project_path).resolve()
        self.user_feedback = user_feedback

        # AI model
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(MODEL_NAME)

        self.workdir = ROOT
        self.artifacts_dir = ROOT / "artifacts"
        self.tool_outputs_dir = self.artifacts_dir / "tool_outputs"
        self.tool_outputs_dir.mkdir(parents=True, exist_ok=True)
    # ---------------------------
    # Static helpers
    # ---------------------------
    @staticmethod            
    def get_latest_hint() -> Path:
        hints_dir = ROOT / "artifacts" / "hints"

        if not hints_dir.exists():
            print(f"No hints directory found: {hints_dir}")
            sys.exit(1)

        hints = sorted(
            hints_dir.glob("hint_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if not hints:
            print("No hint files found in hints/")
            sys.exit(1)

        return hints[0]
    
    @staticmethod
    def get_latest_log():
        logs = sorted((ROOT / "rootcause_logs").glob("*.log"),
                    key=lambda p: p.stat().st_mtime, 
                    reverse=True)
        if not logs:
            return "NO_LOGS_AVAILABLE"
        return logs[0].read_text(encoding="utf-8", errors="ignore")
    
    @staticmethod
    def read_file(path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="ignore")
    
    # ---------------------------
    # Tool wrappers
    # ---------------------------
    def run_tree(self) -> str:
        out = self.tool_outputs_dir / "bug_fix_agent_tree.txt"
        print("[agent] running: project_tree_viewer.py")
        try:
            subprocess.run(
                [sys.executable, "tools/project_tree_viewer.py", str(self.project_path), "--out", str(out)],
                cwd=self.workdir,
                check=True
            )
            return self.read_file(out)
        except Exception as e:
            return f"[ERROR running project_tree_viewer.py] {e}"
    
    def run_file_reader(self, file_path: Path) -> str:
        out = self.tool_outputs_dir / "bug_fix_agent_file.txt"
        print(f"[agent] running: tools/file_reader.py '{file_path}'")
        try:
            subprocess.run(
                [sys.executable, "tools/file_reader.py", str(file_path), "--out", str(out)],
                cwd=self.workdir,
                check=True
            )
            return self.read_file(out)
        except Exception as e:
            return f"[ERROR running file_reader.py] {e}"
   
    def _resolve_file_path(self, file_path: str) -> Path:
        fpath = Path(file_path)
        
        # אם נתיב מוחלט וקיים
        if fpath.is_absolute() and fpath.exists():
            return fpath
        
        # נסה נתיב יחסי ישיר
        direct = (self.project_path / fpath).resolve()
        if direct.exists():
            return direct
        
        # חפש לפי שם קובץ + תיקיית אב
        filename = fpath.name
        parent = fpath.parent.name if fpath.parent.name else None
        
        for found in self.project_path.rglob(filename):
            if parent is None or found.parent.name == parent:
                return found
        
        return direct  # fallback
    
    def run_function_extractor(self, file_path: Path, func_name: str) -> str:
        out = self.tool_outputs_dir / "bug_fix_agent_func.txt"
        print(f"[agent] running: function_extractor.py '{file_path}' '{func_name}'")
        
        try:
            subprocess.run(
                [sys.executable,"tools/function_extractor.py", str(file_path), func_name, "--out", str(out)],
                cwd=self.workdir,
                check=True
            )
            return self.read_file(out)
        except Exception as e:
            return f"[ERROR running function_extractor.py] {e}"
    
    # ---------------------------
    # MAIN EXECUTION (converted)
    # ---------------------------
    def run(self):
        latest_hint = self.get_latest_hint()
        hint_text = self.read_file(latest_hint)

        if self.user_feedback:
            hint_text += f"\n\n--- USER FEEDBACK ---\n{self.user_feedback}"
        
        print(f"[bug-fix-agent] Using latest hint: {latest_hint}")

        tool_outputs: Dict[str, str] = {}
        read_files: set = set()
        called_extracts: set = set()

        for step in range(1, 8):  # up to 7 steps
            ctx_str = json.dumps(tool_outputs, ensure_ascii=False, separators=(',', ':'))[:20000]

            prompt = CONTROLLER_PROMPT.format(hint=hint_text[:20000], context=ctx_str)

            resp = self.model.generate_content(prompt)
            input_tokens = 0
            if resp.usage_metadata:
              input_tokens = int(resp.usage_metadata.prompt_token_count)
              print(f"[agent] Step {step} - Tokens: input={resp.usage_metadata.prompt_token_count}, output={resp.usage_metadata.candidates_token_count}")
            try:
                txt = (resp.text or "").strip()
            except ValueError:
                print("[agent] Empty response from AI, retrying...")
                continue
            if txt.startswith("```"):
                # strip accidental fences
                txt = txt.strip("`")
                if txt.lower().startswith("json"):
                    txt = txt[4:].strip()
            try:
                msg = json.loads(txt)
            except Exception as e:
                print(f"[agent] AI returned non-JSON at step {step}", file=sys.stderr)
                
                # נסה לחלץ ג'ייסון מתוך הטקסט
                json_match = re.search(r'\{[\s\S]*\}', txt)
                if json_match:
                    try:
                        msg = json.loads(json_match.group())
                        print(f"[agent] Extracted JSON from response")
                    except:
                        pass
                    else:
                        continue
                
                # אם לא הצלחנו - שמור את התשובה הטקסטואלית
                fixes_dir = ROOT / "artifacts" / "bug_fixes"
                fixes_dir.mkdir(exist_ok=True)
                timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
                out_path = fixes_dir / f"fix_{timestamp}.json"
                
                out_path.write_text(
                    json.dumps({
                        "type": "analysis",
                        "text": txt,
                        "reason": "AI provided analysis instead of fix"
                    }, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
                
                print(f"[agent] Saved AI analysis to: {out_path}")
                return input_tokens
            action = msg.get("action", "")
            # ---------------------------
            # FINAL OUTPUT
            # ---------------------------
            if action == "final":
                result = msg.get("result") or {}

                # create bug_fixes folder next to bug_fix_agent.py
                fixes_dir = ROOT / "artifacts" / "bug_fixes"
                fixes_dir.mkdir(exist_ok=True)

                # timestamped filename
                timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
                out_path = fixes_dir / f"fix_{timestamp}.json"

                # write result to file
                out_path.write_text(
                    json.dumps(result, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )

                print(f"[agent] Bug fix written to: {out_path}")
                return  input_tokens
            
            # ---------------------------
            # TOOL REQUESTS
            # ---------------------------
            if action == "read_logs":
                print("[agent] AI requested LAST RESORT log access")
                tool_outputs["LOG_CONTENT"] = self.get_latest_log()
                continue
            
            if action == "run_tree":
                tool_outputs["PROJECT_TREE"] = self.run_tree()[:20000]  # cap
                continue

            if action == "read_file":
                params = msg.get("params") or {}
                file_path = params.get("file_path")
                
                if not file_path:
                    print(f"[agent] Missing file_path for read_file at step {step}", file=sys.stderr)
                    sys.exit(1)
                
                fpath = self._resolve_file_path(file_path)
                
                if str(fpath) in read_files:
                    print(f"[agent] ⚠ Already read {fpath.name}, skipping")
                    tool_outputs["DUPLICATE_READ"] = f"Already read {fpath.name}"
                    continue
                
                read_files.add(str(fpath))
                content = self.run_file_reader(fpath)
                key = f"FILE::{fpath}"
                tool_outputs[key] = content[:20000]
                continue

            if action == "extract_function":
                params = msg.get("params") or {}
                file_path = params.get("file_path")
                func_name = params.get("function_name")
                if not file_path or not func_name:
                    print(f"[agent] Missing params for extract_function at step {step}", file=sys.stderr)
                    sys.exit(1)
                
                fpath = self._resolve_file_path(file_path)
                key = f"FUNCTION::{fpath}::{func_name}"
                
                if key in called_extracts:
                    print(f"[agent] Skipping duplicate call: {func_name}() from {fpath.name}")
                    tool_outputs["DUPLICATE_CALL"] = f"Already retrieved {func_name} from {fpath.name}"
                    continue
                called_extracts.add(key)
                
                out = self.run_function_extractor(fpath, func_name)
                tool_outputs[key] = out[:60000]
                continue
            if action == "ask_trace_agent":
                if trace_questions >= MAX_TRACE_QUESTIONS:
                    print(f"[agent] Trace questions limit reached ({MAX_TRACE_QUESTIONS})")
                    tool_outputs["TRACE_LIMIT"] = "Question limit reached"
                    continue
                
                params = msg.get("params") or {}
                question = params.get("question")
                
                if not question:
                    print(f"[agent] Missing question for ask_trace_agent at step {step}")
                    continue
                
                trace_questions += 1
                print(f"[agent] Asking trace agent: {question[:50]}...")
                
                trace_agent = AiTraceAgent()
                answer, tokens = trace_agent.answer_question(question)
                input_tokens += tokens
                
                tool_outputs["TRACE_ANSWER"] = answer[:5000]
                continue
            # Unknown action
            print(f"[agent] Unknown action from AI: {action}", file=sys.stderr)
            print(json.dumps(msg, ensure_ascii=False, indent=2))
            sys.exit(1)

        print("[agent] Reached max steps, requesting final answer...")

        ctx_str = json.dumps(tool_outputs, ensure_ascii=False, separators=(',', ':'))[:20000]
        final_prompt = f"""You have reached the maximum number of steps.
        Based on all the context you gathered, provide your BEST GUESS for a fix.
        If you cannot provide a fix, explain what information is missing and what the problem seems to be.

        You MUST return a final JSON response now:
        {{
        "action": "final",
        "result": {{
            "functions_to_edit": ["file.ts:funcName"],
            "reason": "your best explanation",
            "patch_suggestion": "your best guess for the fix, or explanation of the problem"
        }}
        }}

        --- HINT ---
        {hint_text[:10000]}

        --- CONTEXT ---
        {ctx_str}
        """

        resp = self.model.generate_content(final_prompt)
        if resp.usage_metadata:
            input_tokens += int(resp.usage_metadata.prompt_token_count)

        txt = (resp.text or "").strip()
        if txt.startswith("```"):
            txt = txt.strip("`")
            if txt.lower().startswith("json"):
                txt = txt[4:].strip()

        try:
            msg = json.loads(txt)
            result = msg.get("result") or msg
        except:
            result = {
                "functions_to_edit": [],
                "reason": "Agent could not complete analysis",
                "patch_suggestion": txt[:2000]
            }

        fixes_dir = ROOT / "artifacts" / "bug_fixes"
        fixes_dir.mkdir(exist_ok=True)
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        out_path = fixes_dir / f"fix_{timestamp}.json"

        out_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        print(f"[agent] Final answer saved to: {out_path}")
        return input_tokens
                
if __name__ == "__main__":
    if "--project" not in sys.argv:
        print("Usage: python bug_fix_agent.py --project /path/to/project")
        sys.exit(1)

    project_path = None
    for i, a in enumerate(sys.argv):
        if a == "--project" and i + 1 < len(sys.argv):
            project_path = sys.argv[i + 1]

    agent = BugFixAgent(project_path)
    agent.run()