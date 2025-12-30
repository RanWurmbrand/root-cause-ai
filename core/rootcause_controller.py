# rootcause_controller.py

from .project_runner import ProjectRunner
from agents.ai_trace_agent import AiTraceAgent
from agents.bug_fix_agent import BugFixAgent
from messaging.bugfix_notifier import BugFixMessageBuilder
from messaging.telegram_manager import TelegramManager
from core.code_applier import CodeApplier
from core.git_manager import GitManager
from dotenv import load_dotenv
import os
from pathlib import Path
load_dotenv()
ROOT = Path(__file__).resolve().parents[1]

class RootCauseController:
    def __init__(self, project_path: str, command: str = "npm test"):
        self.project_path = project_path
        self.command = command
        self.git_manager = None
        self.code_applier = None
        self.flag= False
        try:
            self.git_manager = GitManager(self.project_path)
            print("[controller] ✓ Git repository detected")
        except RuntimeError as e:
            print(f"[controller] ⚠ Git not available: {e}")
            print("[controller] Fix & Rerun will be disabled")
        
        # Initialize code applier
        self.code_applier = CodeApplier(self.project_path, ROOT)



    def apply_fix_and_commit(self) -> bool:
        """
        Apply the suggested fix to the codebase and commit it
        Returns True if successful, False otherwise
        """
        if not self.git_manager:
            print("[controller] ✗ Cannot apply fix: Git not available")
            return False
        
        # Step 1: Prepare git (create/switch to branch)
        print("\n[controller] === Preparing Git Repository ===")
        if not self.git_manager.prepare_for_fix():
            print("[controller] ✗ Failed to prepare git repository")
            return False
        
        # Step 2: Apply the fix
        print("\n[controller] === Applying Fix ===")
        result = self.code_applier.apply_fix()
        
        if not result["success"]:
            print(f"[controller] ✗ Failed to apply fix: {result.get('error')}")
            return False
        
        print(f"[controller] ✓ Applied fix to: {result['file']}")
        
        # Step 3: Commit the changes
        print("\n[controller] === Committing Changes ===")
        if not self.git_manager.commit_fix(result['file'], result['reason']):
            print("[controller] ✗ Failed to commit changes")
            return False
        
        print("[controller] ✓ Fix applied and committed successfully")
        return True

    def run_once(self):
        # 1. Run project tests
        if self.flag:
            runner = ProjectRunner(self.project_path, self.command)
            runner.run()

        # 2. Run AI trace agent (creates latest hint)
        trace_agent = AiTraceAgent()
        trace_agent.run()

        # 3. Run AI bug fix agent (creates latest fix)
        fix_agent = BugFixAgent(self.project_path)
        fix_agent.run()

        # 4. Build message
        builder = BugFixMessageBuilder()
        message = builder.build_message()

        # 5. Send to Telegram and wait for user action
        tm = TelegramManager()
        tm.send_bugfix_message(message)
        user_choice = tm.wait_for_user_response()

        return user_choice

    def start(self):
        while True:
            action = self.run_once()

            if action == "rerun":
                print("[controller] User selected RERUN → starting again...")
                continue

            elif action == "fix_and_rerun":
                print("\n[controller] User selected FIX & RERUN")
                
                # Apply the fix and commit
                if self.apply_fix_and_commit():
                    print("[controller] ✓ Fix applied successfully")
                    print("[controller] → Re-running tests...\n")
                else:
                    print("[controller] ✗ Fix application failed")
                    print("[controller] → Re-running tests anyway to see current state...\n")

            elif action == "terminate":
                print("[controller] Terminate requested → stopping.")
                break


if __name__ == "__main__":
    PROJECT_PATH = os.getenv("PROJECT_PATH")
    EXECUTE_COMMAND = os.getenv("EXECUTE_COMMAND")

    controller = RootCauseController(PROJECT_PATH, EXECUTE_COMMAND)
    controller.start()
