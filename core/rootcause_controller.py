# rootcause_controller.py

from .project_runner import ProjectRunner
from agents.ai_trace_agent import AiTraceAgent
from agents.bug_fix_agent import BugFixAgent
from messaging.bugfix_notifier import BugFixMessageBuilder
from messaging.telegram_manager import TelegramManager
from dotenv import load_dotenv
import os
load_dotenv()


class RootCauseController:
    def __init__(self, project_path: str, command: str = "npm test"):
        self.project_path = project_path
        self.command = command

    def run_once(self):
        # 1. Run project tests
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
                print("[controller] Fix & Rerun not implemented → performing normal rerun...")
                continue

            elif action == "terminate":
                print("[controller] Terminate requested → stopping.")
                break


if __name__ == "__main__":
    PROJECT_PATH = os.getenv("PROJECT_PATH")
    EXECUTE_COMMAND = os.getenv("EXECUTE_COMMAND")

    controller = RootCauseController(PROJECT_PATH, EXECUTE_COMMAND)
    controller.start()
