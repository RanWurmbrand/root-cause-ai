from core.rootcause_controller import RootCauseController
from dotenv import load_dotenv
import os

load_dotenv()

if __name__ == "__main__":
    PROJECT_PATH = os.getenv("PROJECT_PATH")
    EXECUTE_COMMAND = os.getenv("EXECUTE_COMMAND", "npm test")

    if not PROJECT_PATH:
        print("Error: PROJECT_PATH not set in .env file")
        print("Please create a .env file with:")
        print("  PROJECT_PATH=/path/to/your/project")
        print("  EXECUTE_COMMAND=npx vitest")
        print("  GEMINI_API_KEY=your_key")
        print("  TELEGRAM_BOT_TOKEN=your_token")
        print("  TELEGRAM_CHAT_ID=your_chat_id")
        exit(1)

    controller = RootCauseController(PROJECT_PATH, EXECUTE_COMMAND)
    controller.start()