# Root Cause AI 🔍🤖

An intelligent debugging assistant that automatically detects, analyzes, and suggests fixes for test failures in your projects using AI-powered agents.

## 🌟 Features

- **Automated Test Execution**: Runs your project tests and captures detailed logs
- **AI-Powered Root Cause Analysis**: Uses Google's Gemini AI to analyze test failures and identify root causes
- **Intelligent Bug Fix Suggestions**: Agentic system that explores your codebase and proposes minimal, targeted fixes
- **Interactive Telegram Notifications**: Get real-time updates with actionable options directly in Telegram
- **Minimal Context Usage**: Smart tool selection to reduce token consumption and API costs

## 📋 Prerequisites

- Python 3.8+
- Node.js project (currently supports `npm test` command)
- Google Gemini API key
- Telegram bot token and chat ID

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/root-cause-ai.git
cd root-cause-ai
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a `.env` file in the root directory:
```env
# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Project Configuration
PROJECT_PATH=/path/to/your/project
EXECUTE_COMMAND=npm test
```

#### Getting Your API Keys:

**Google Gemini API Key:**
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Get API Key" or "Create API Key"
4. Copy your API key to the `.env` file

**Telegram Bot Token & Chat ID:**
1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow the instructions to create a new bot
3. Copy the **bot token** provided by BotFather to `TELEGRAM_BOT_TOKEN`
4. To get your Chat ID:
   - Search for [@userinfobot](https://t.me/userinfobot) on Telegram
   - Start a chat with it and it will display your Chat ID
   - Copy the ID to `TELEGRAM_CHAT_ID`

### 4. Run the Controller
```bash
python -m core.rootcause_controller
```

The system will:
1. Execute your tests
2. Analyze any failures
3. Generate fix suggestions
4. Send you a Telegram message with three options:
   - 🔁 **Rerun**: Run tests again
   - 🛠️ **Fix & Rerun**: Apply the suggested fix and rerun (coming soon)
   - ⛔ **Terminate**: Stop the debugging cycle

## 📁 Project Structure
```
root-cause-ai/
├── agents/
│   ├── ai_trace_agent.py       # Analyzes test logs for root causes
│   └── bug_fix_agent.py        # Suggests targeted bug fixes
├── core/
│   ├── project_runner.py       # Executes project tests
│   └── rootcause_controller.py # Orchestrates the debugging workflow
├── messaging/
│   ├── bugfix_notifier.py      # Formats bug fix messages
│   └── telegram_manager.py     # Handles Telegram interactions
├── tools/
│   ├── file_reader.py          # Reads full file contents
│   ├── function_extractor.py   # Extracts specific functions
│   └── project_tree_viewer.py  # Generates project structure
└── artifacts/
    ├── bug_fixes/              # Generated fix suggestions
    ├── hints/                  # AI-generated hints
    ├── rootcause_logs/         # Test execution logs
    └── tool_outputs/           # Intermediate tool outputs
```

## 🔧 How It Works

1. **Test Execution**: `project_runner.py` runs your test suite and saves logs
2. **Log Analysis**: `ai_trace_agent.py` sends logs to Gemini AI, which identifies the root cause
3. **Fix Generation**: `bug_fix_agent.py` autonomously:
   - Explores your project structure
   - Extracts relevant code
   - Generates a minimal patch suggestion
4. **User Notification**: Results are sent to Telegram with actionable buttons
5. **Loop or Terminate**: Based on your choice, the system reruns or stops

## 🎯 Key Components

### AI Trace Agent
- Analyzes test failure logs
- Identifies root causes vs. cascading errors
- Generates structured hints with file/function/line information

### Bug Fix Agent
- Autonomous agent with access to project exploration tools
- Requests only the context it needs (minimizing token usage)
- Produces unified diff patches for targeted fixes

### Telegram Integration
- Real-time notifications with HTML formatting
- Interactive buttons for workflow control
- Waits for user decision before proceeding

## 🤝 Contributing

I'd love your help! Here are areas where contributions would be especially valuable:

### High Priority
- **Implement Auto-Fix**: Complete the "Fix & Rerun" button functionality to automatically apply suggested patches
- **Token Optimization**: Further reduce Gemini API token consumption through:
  - Smarter context selection
  - More efficient prompts
  - Caching strategies
- **Multi-Language Support**: Extend beyond Node.js to support Python pytest, Java JUnit, etc.

### Medium Priority
- **Enhanced Fix Validation**: Add confidence scoring for fix suggestions
- **Patch Preview**: Show before/after diffs more clearly
- **Configuration UI**: Web interface for easier setup
- **Cost Tracking**: Monitor and report API usage costs

### Nice to Have
- **CI/CD Integration**: GitHub Actions / GitLab CI support
- **Multiple LLM Support**: Add OpenAI, Anthropic Claude options
- **Historical Analysis**: Track fix success rates over time

Feel free to open issues or submit PRs for any improvements!

## 📝 License

MIT License - feel free to use this project however you'd like!

## 🐛 Known Limitations

- Currently only supports Node.js projects with `npm test`
- Requires manual application of suggested fixes
- Limited to text-based analysis (no screenshot/visual debugging)
- Gemini API rate limits may affect rapid iterations

## 💡 Tips

- Start with a small test suite to validate the setup
- Check `artifacts/` folders for detailed outputs if something goes wrong
- The system works best with clear, descriptive test failure messages
- Consider setting up API spending limits on your Google Cloud account

---

## 📬 Contact & Support

I'd love to hear your feedback! Whether you have questions about the architecture, suggestions for the AI agents, or just want to connect — feel free to reach out.

* 📧 **Email**: [ranwurembrand@gmail.com](mailto:ranwurembrand@gmail.com) or [rwurmbra@redhat.com](mailto:rwurmbra@redhat.com)
* 💼 **LinkedIn**: [Ran Wurmbrand](https://www.linkedin.com/in/ranwurmbrand/)
* 🐙 **GitHub**: [@RanWurmbrand](https://github.com/RanWurmbrand/) or [@RanWurm](https://github.com/RanWurm)

Don't hesitate to open an issue if you encounter bugs!
