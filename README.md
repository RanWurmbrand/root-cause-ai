# Root Cause AI 🔍🤖

An intelligent debugging assistant that automatically detects, analyzes, and suggests fixes for test failures in your projects using AI-powered multi-agent architecture.

## 🌟 Features

- **Automated Test Execution**: Runs your project tests and captures detailed logs
- **AI-Powered Root Cause Analysis**: Uses Google's Gemini AI to analyze test failures and identify root causes
- **Multi-Agent Communication**: Bug-fix agent can query the trace agent for deeper log analysis
- **Intelligent Bug Fix Suggestions**: Agentic system that explores your codebase and proposes minimal, targeted fixes
- **Automated Fix Application**: Automatically applies suggested patches to your codebase with Git version control
- **Safe Git Branching**: All fixes are committed to a separate `rootcause-fixes` branch, preserving your main branch
- **Interactive Telegram Notifications**: Real-time updates with actionable options including user suggestions
- **Token Optimization**: Smart context extraction and duplicate call prevention to reduce API costs
- **Output Log Collection**: Optional collection of VS Code extension output logs for deeper debugging

## 📋 Prerequisites

- Python 3.8+
- Node.js project (currently supports `npm test` command)
- **Git repository** (required for Fix & Rerun feature)
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

# Optional: Output Log Collection (for VS Code extensions)
COLLECT_OUTPUT_LOGS=true
OUTPUT_LOG_NAME=Konveyor Extension for VSCode
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

### 4. Initialize Git in Your Project (Required for Fix & Rerun)
```bash
cd /path/to/your/project
git init  # If not already a git repository
git add .
git commit -m "Initial commit"
```

### 5. Run the Controller
```bash
python -m core.rootcause_controller
```

The system will:
1. Execute your tests
2. Analyze any failures
3. Generate fix suggestions
4. Send you a Telegram message with four options:
   - 🔄 **Rerun**: Run tests again
   - 🛠️ **Fix & Rerun**: Apply the suggested fix, commit to Git, and rerun tests
   - 💬 **Suggest**: Provide your own guidance to help the AI agent
   - ⛔ **Terminate**: Stop the debugging cycle

## 📁 Project Structure
```
root-cause-ai/
├── agents/
│   ├── ai_trace_agent.py       # Analyzes test logs for root causes
│   └── bug_fix_agent.py        # Suggests targeted bug fixes
├── core/
│   ├── project_runner.py       # Executes project tests
│   ├── rootcause_controller.py # Orchestrates the debugging workflow
│   ├── git_manager.py          # Manages Git branching and commits
│   └── code_applier.py         # Applies patches to codebase
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
    ├── output_logs/            # VS Code extension output logs
    └── tool_outputs/           # Intermediate tool outputs
```

## 🔧 How It Works

### Core Workflow

1. **Test Execution**: `project_runner.py` runs your test suite and saves logs. Optionally collects VS Code extension output logs.

2. **Log Analysis**: `ai_trace_agent.py` sends logs to Gemini AI, which identifies the root cause. The agent can optionally use tools like `read_output_log` for deeper analysis when output logs are available.

3. **Fix Generation**: `bug_fix_agent.py` autonomously:
   - Explores your project structure
   - Extracts relevant code using smart file resolution
   - Can query the trace agent for additional log context (up to 3 questions)
   - Prevents duplicate tool calls to save tokens
   - Generates a minimal unified diff patch

4. **User Notification**: Results are sent to Telegram with actionable buttons. Long messages (>4000 chars) are sent as document attachments.

5. **Fix Application** (if "Fix & Rerun" selected):
   - `git_manager.py` creates/switches to `rootcause-fixes` branch
   - `code_applier.py` parses the unified diff and applies the patch using intelligent line matching
   - Changes are automatically committed with a descriptive message
   - Tests are re-run to validate the fix

6. **User Feedback** (if "Suggest" selected):
   - User provides guidance via Telegram
   - Bug-fix agent runs again with user feedback incorporated
   - No test re-run, just re-analysis with new context

7. **Loop or Terminate**: Based on your choice, the system continues or stops. Session auto-terminates at 13M tokens to prevent runaway costs.

### Multi-Agent Communication

The bug-fix agent can query the trace agent when it needs more context about errors:

```
Bug-Fix Agent: "What was the exact error message for the timeout?"
     ↓
Trace Agent: [Analyzes logs] → "TimeoutError: Navigation exceeded 30000ms"
     ↓
Bug-Fix Agent: [Uses answer to refine fix suggestion]
```

This is limited to 3 questions per session to control API costs.

## 🎯 Key Components

### AI Trace Agent
- Analyzes test failure logs using Gemini AI
- Identifies root causes vs. cascading errors
- Generates structured hints with file/function/line information
- Supports optional `read_output_log` tool for VS Code extension debugging
- Extracts only error-relevant log sections to minimize token usage
- Can answer questions from the bug-fix agent about specific log details

### Bug Fix Agent
- Autonomous agent with access to project exploration tools
- Requests only the context it needs (minimizing token usage)
- Prevents duplicate tool calls for the same file/function
- Can ask the trace agent questions about the logs
- Supports user feedback to guide fix suggestions
- Produces unified diff patches for targeted fixes
- Provides best-effort analysis when max steps reached

### Git Manager
- Creates separate `rootcause-fixes` branch on first fix
- Preserves main branch integrity
- Auto-commits with descriptive messages
- Supports incremental fixes with full version history

### Code Applier
- Parses unified diff format patches (+/- lines)
- Groups consecutive changes into hunks
- Locates and replaces code with intelligent whitespace normalization
- Handles multi-line replacements
- Preserves original indentation

### Telegram Integration
- Real-time notifications with HTML formatting
- Interactive buttons for workflow control (Rerun, Fix & Rerun, Suggest, Terminate)
- Sends long messages as document attachments
- Waits for user decision before proceeding
- Error notifications when agents crash

### Token Optimization
- Extracts only error-related lines from logs instead of full content
- Caps tool outputs (20k chars for files, 60k for functions)
- Prevents duplicate tool calls
- Limits expensive operations (3 trace questions, 3 output log reads)
- Session token limit of 13M to prevent runaway costs

## 🔧 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token from BotFather |
| `TELEGRAM_CHAT_ID` | Yes | Your Telegram chat ID |
| `PROJECT_PATH` | Yes | Path to your project directory |
| `EXECUTE_COMMAND` | Yes | Command to run tests (e.g., `npm test`) |
| `COLLECT_OUTPUT_LOGS` | No | Set to `true` to collect VS Code output logs |
| `OUTPUT_LOG_NAME` | No | Name pattern to match output log files |

## 🤝 Contributing

I'd love your help! Here are areas where contributions would be especially valuable:

### High Priority
- **Build Support**: Extend beyond test failures to support build error analysis and fixes
- **Multi-Notification Channels**: Add Slack and email notifications alongside Telegram
- **Token Optimization**: Further reduce Gemini API token consumption through smarter context selection and caching
- **Multi-Language Support**: Extend beyond Node.js to support Python pytest, Java JUnit, Go tests, etc.

### Medium Priority
- **Enhanced Fix Validation**: Add confidence scoring for fix suggestions
- **Rollback Support**: Automatically rollback if tests fail after applying fix
- **Patch Preview**: Show before/after diffs more clearly in notifications
- **Configuration UI**: Web interface for easier setup
- **Cost Tracking**: Monitor and report API usage costs per session

### Nice to Have
- **CI/CD Integration**: GitHub Actions / GitLab CI support
- **Multiple LLM Support**: Add OpenAI, Anthropic Claude, Grok options
- **Historical Analysis**: Track fix success rates over time
- **Web Dashboard**: Visualize debugging sessions and fix history
- **Parallel Analysis**: Run multiple fix strategies simultaneously

Feel free to open issues or submit PRs for any improvements!

## 📄 License

MIT License - feel free to use this project however you'd like!

## 🛠 Known Limitations

- Currently only supports Node.js projects with configurable test commands
- Limited to text-based analysis (no screenshot/visual debugging)
- Gemini API rate limits may affect rapid iterations
- Fix application requires near-exact code matching
- Git repository required for automated fix application
- Session limited to 13M tokens to prevent excessive costs

## 💡 Tips

- Start with a small test suite to validate the setup
- Check `artifacts/` folders for detailed outputs if something goes wrong
- The system works best with clear, descriptive test failure messages
- Consider setting up API spending limits on your Google Cloud account
- Review fixes in the `rootcause-fixes` branch before merging to main
- Use `git diff main..rootcause-fixes` to see all applied fixes
- Use the "Suggest" button to guide the AI when it's stuck
- Enable `COLLECT_OUTPUT_LOGS` for VS Code extension debugging

---

## 📬 Contact & Support

I'd love to hear your feedback! Whether you have questions about the architecture, suggestions for the AI agents, or just want to connect — feel free to reach out.

* 📧 **Email**: [ranwurembrand@gmail.com](mailto:ranwurembrand@gmail.com) or [rwurmbra@redhat.com](mailto:rwurmbra@redhat.com)
* 💼 **LinkedIn**: [Ran Wurmbrand](https://www.linkedin.com/in/ranwurmbrand/)
* 🙂 **GitHub**: [@RanWurmbrand](https://github.com/RanWurmbrand/) or [@RanWurm](https://github.com/RanWurm)
* 🌐 **Website**: [My Portfolio](https://ran-wurmbrand.vercel.app/)

Don't hesitate to open an issue if you encounter bugs!
