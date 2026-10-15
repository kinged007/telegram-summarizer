# Telegram Summarizer

[![CI](https://github.com/kinged007/telegram-summarizer/actions/workflows/ci.yml/badge.svg)](https://github.com/kinged007/telegram-summarizer/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Summarize Telegram channel and group conversations with an LLM. Collect the last N days of messages from any set of chats, build a prompt with configurable templates, send it to OpenAI/Anthropic/Groq via LiteLLM, and display the summary in the console or forward it to another Telegram chat.

![Demo](./docs/screenshot.png)
> Screenshot to be added — shows Rich progress bars and a formatted summary panel.

## Features

- AI summaries via any LiteLLM-supported provider (OpenAI, Anthropic, Groq, ...)
- Multi-channel and topic-aware fetching (Telegram topics/threads via `ID_topicId`)
- Named chats, prompt templates, and job presets in `Templates.txt`
- Automation-ready: cron and macOS launchd examples included
- Cost and token tracking per request
- Mock mode for offline testing

## Requirements

- Python 3.10+
- A Telegram API ID/hash from https://my.telegram.org
- An LLM API key (OpenAI, Anthropic, etc.)

## Install

```bash
# Clone
git clone https://github.com/kinged007/telegram-summarizer.git
cd telegram-summarizer

# Copy env and fill in your credentials
cp sample.env .env   # then edit .env

# Create templates (optional, friendly names for chats/prompts)
cp Templates.sample.txt Templates.txt

# One-shot helper (creates venv, installs deps, runs the app)
sh run.sh --chats=-1001234567890 --days 3

# Or manual setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python summarize.py --chats=-1001234567890 --mock   # dry run, no API call
```

## Usage

```bash
# Summarize one chat, print to console
python summarize.py --chats -1001234567890

# Multiple chats, send result to another chat
python summarize.py --chats -1001234567890,-1009876543210 --send=-1009876543210

# Use a named chat and prompt template from Templates.txt
python summarize.py --chats John --prompt_template Technical

# Look back 7 days with extra instructions
python summarize.py --chats John --days 7 --prompt="Focus on decisions and action items"

# Run a saved job preset
python summarize.py --job DailyUpdate
python summarize.py --job DailyUpdate,WeeklyReport

# Mock mode (no LLM call) and debug logging
python summarize.py --chats John --mock
python summarize.py --chats John --debug
```

### Templates.txt

`Templates.txt` maps friendly names to chat IDs, prompt templates, and full job presets:

```
chat:John=-1001234567890
chat:TeamChat=-1001122334455
prompt:Technical=Please summarize the technical discussions ...
job:DailyUpdate=--chats John --send TeamChat --days 1 --prompt_template Daily
```

Copy `Templates.sample.txt` to get started. See the Usage and Templates sections below for the full reference.

### Environment variables (via `.env`)

| Variable | Required | Example |
|---|---|---|
| `TELEGRAM_API_ID` | yes | `10305366` |
| `TELEGRAM_API_HASH` | yes | `c40842c619a...` |
| `LLM_PROVIDER` | yes | `openai` |
| `LLM_MODEL` | yes | `gpt-4o-mini` |
| `LLM_API_KEY` | yes | `sk-proj-...` |
| `PROMPT_SYSTEM` | no | `You are a helpful summarizing assistant.` |
| `PROMPT_TEXT` | no | `Please summarize the conversations.` |
| `PROXY` | no | `http://proxy:8080` |

## How it is tested

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
ruff check .
mypy src
```

CI (`.github/workflows/ci.yml`) runs `pytest`, `ruff check`, and `mypy` on every push and pull request to `master` (Python 3.10 + 3.11).

Mock mode exercises the full pipeline without Telegram or LLM credentials: `python summarize.py --chats John --mock` and `pytest -q` both work offline.

For detailed CI and test commands, see [AGENTS.md](AGENTS.md).

---

## How It Works

The script follows this workflow:

1. **Setup**: Loads environment variables and parses command line arguments
2. **Connection**: Connects to Telegram using your API credentials
3. **Message Collection**: Fetches messages from the specified chats for the specified number of days
4. **Prompt Creation**: Combines the collected messages with system and user prompts
5. **AI Processing**: Sends the prompt to the configured LLM provider (OpenAI, Anthropic, etc.)
6. **Result Handling**: Displays the summary in the console and optionally sends it to specified Telegram chats
7. **Logging**: Records detailed information about the process in log files

This script signs into a user's account. It has not been tested with a Bot account, but should work in theory.

To get the channel IDs, you can:
1. Forward any message from the channel you want to work with to an ID Bot (e.g., @username_to_id_bot). The ID should start with -100 for groups or channels.
2. Use Telegram usernames directly (e.g., @username) in your Templates.txt file.
3. Use the special 'me' value to refer to your own account.

### Topic-Specific Chats

The script supports topic-specific chats (also known as threads or sub-groups) by using an underscore followed by the topic ID. For example: `-1001234567_789` where `-1001234567` is the main chat ID and `789` is the topic ID.

**Important:** When using topic-specific chat IDs on the command line, you must use the equals sign format:

```bash
# CORRECT way to specify a topic-specific chat ID
python summarize.py --chats=-1001234567_789

# This will NOT work correctly
python summarize.py --chats -1001234567_789
```

To find a topic ID:
1. Open the topic in Telegram
2. Look at the URL in your browser (if using Telegram Web or Desktop) - the topic ID is in the URL
3. Or copy a message link from the topic - the topic ID will be in the link
4. You can also see it in the address bar when viewing topic info

## Command Line Arguments

| Argument | Description | Required | Default |
|----------|-------------|----------|---------|
| `--chats` | Chat IDs or names from Templates.txt to summarize from (can be comma-separated or multiple values) | Yes* | None |
| `--send` | Chat IDs or names from Templates.txt where the summary should be sent (can be comma-separated or multiple values) | No | None |
| `--days` | Number of days to look back for messages | No | 3 |
| `--prompt` | Additional instructions for the AI summarizer | No | "" |
| `--prompt_template` | Name(s) of prompt template(s) from Templates.txt to use instead of the default prompt | No | None |
| `--debug` | Enable debug mode to see detailed information | No | False |
| `--mock` | Use mock response instead of calling the LLM API (for testing) | No | False |
| `--job` | Name(s) of job template(s) from Templates.txt to execute (can be comma-separated or multiple values) | No | None |

*Not required if using `--job` argument

#### Examples

```bash
# Basic usage - summarize messages from a chat and display in console
python summarize.py --chats -1001234567890

# Summarize messages from multiple chats (comma-separated)
python summarize.py --chats -1001234567890,-1009876543210

# Summarize messages from multiple chats (separate arguments)
python summarize.py --chats -1001234567890 -1009876543210

# Summarize messages from a topic-specific chat (with underscore)
# IMPORTANT: Note the equals sign (=) when using topic IDs with underscores
python summarize.py --chats=-1001234567890_123

# Summarize messages and send to another chat
python summarize.py --chats -1001234567890 --send=-1009876543210

# Summarize messages and send to a topic-specific chat
# Note the equals sign (=) for both arguments with underscores
python summarize.py --chats=-1001234567890 --send=-1009876543210_123

# Look back more days (default is 3)
python summarize.py --chats -1001234567890 --days=7

# Add custom instructions to the prompt
python summarize.py --chats -1001234567890 --prompt="Focus on technical discussions and ignore small talk"

# Use a predefined prompt template
python summarize.py --chats -1001234567890 --prompt_template=Technical

# Use multiple prompt templates (they will be combined)
python summarize.py --chats -1001234567890 --prompt_template=Technical,Meeting

# Enable debug mode for detailed information
python summarize.py --chats -1001234567890 --debug

# Use mock mode for testing (no API call)
python summarize.py --chats -1001234567890 --mock

# Use a predefined job template from Templates.txt
python summarize.py --job DailyUpdate

# Run multiple job templates (comma-separated)
python summarize.py --job DailyUpdate,WeeklyReport

# Run multiple job templates (separate arguments)
python summarize.py --job DailyUpdate WeeklyReport
```

### Using Templates.txt

You can use the `Templates.txt` file to store chat names, prompt templates, and job templates. This allows you to use friendly names instead of numeric IDs when running the script, use predefined prompt templates, and create reusable job configurations.

The Templates.txt file uses a simple key-value format with prefixes:
```
# Comments start with #
chat:ChatName=ChatID  # Can be numeric ID, @username, or 'me'
prompt:TemplateName=Template Text
job:JobName=--argument1 value1 --argument2 value2
```

For example:
```
# Chat IDs
chat:John=-1001234567890
chat:TeamChat=-1009876543210
chat:ProjectTopic=-1001234567890_123  # Topic-specific chat (underscore format works fine in Templates.txt)
chat:TelegramSupport=@telegram  # Using username directly
chat:MyAccount=me  # Your own account

# Prompt Templates
prompt:Technical=Please summarize the technical discussions in these conversations.
prompt:Meeting=Please summarize this conversation as if it were meeting minutes.

# Job Templates
job:DailyUpdate=--chats John --send TeamChat --days 1 --prompt_template Daily
job:WeeklyReport=--chats John,ProjectDiscussion --send TeamChat --days 7 --prompt_template Weekly
```

#### Special Template Names

You can override the default system and user prompts by adding these special templates:

```
# Override environment variables with templates
prompt:PROMPT_SYSTEM=You are an expert AI assistant specialized in summarizing Telegram conversations.
prompt:PROMPT_TEXT=Please analyze these Telegram conversations and provide a comprehensive summary.
```

The script will check for these templates first, then fall back to environment variables, and finally use hardcoded defaults if neither is available.

## Advanced Topics

### Logging

The script creates detailed logs in the `logs` directory. Each run generates a timestamped log file with debug information, even when not running in debug mode.

### Automation (cron / launchd)

See the Usage section for quick starts. For scheduled runs, prefer job presets:

```
# cron: daily 08:00
0 8 * * * cd /full/path/to/telegram-summarizer && ./run.sh --job DailyUpdate >> logs/cron.log 2>&1
```

On macOS, use `launchd` with a `~/Library/LaunchAgents/com.username.telegramsummarizer.plist` — see the cron/launchd guide in the docs for a full example.

### Troubleshooting

1. **Authentication Error**: Check `TELEGRAM_API_ID` / `TELEGRAM_API_HASH`.
2. **Chat ID Not Found**: Try a name from `Templates.txt` instead of a raw ID.
3. **LLM API Error**: Verify `LLM_API_KEY` / `LLM_PROVIDER` / `LLM_MODEL`.
4. **No Messages Found**: Increase `--days`.
5. **Topic chat underscore**: Use `python summarize.py --chats=-1001234567_789` (equals sign required).

Add `--debug` for verbose output and `logs/` for per-run log files.

## License

MIT — see [LICENSE](LICENSE).
