# Telegram Message Summarizer

This script connects to specific Telegram channels/groups, collects the last messages from a predefined number of days, then compiles them into a prompt for an LLM (Large Language Model). The AI-generated summary can then be displayed in the console and/or sent to designated Telegram channels.

## ✨ Features

- 🤖 **AI-Powered Summaries**: Leverages modern LLMs to create concise, intelligent summaries of Telegram conversations
- 📱 **Multi-Channel Support**: Collect messages from multiple Telegram channels, groups, and topics in a single run
- 📊 **Progress Tracking**: Beautiful progress bars show real-time status of message collection and processing
- 📝 **Customizable Prompts**: Tailor summaries with custom instructions or predefined templates
- 🔄 **Job Templates**: Create and run predefined configurations for recurring summarization tasks
- 📅 **Automation Ready**: Easily schedule with cron jobs or launchd for regular summaries
- 📤 **Flexible Output**: View summaries in the console or send them directly to Telegram channels
- 📈 **Cost Tracking**: Monitor token usage and costs for each LLM request
- 🧪 **Mock Mode**: Test functionality without making actual API calls
- 📊 **Detailed Logging**: Comprehensive logging system for troubleshooting
- 👤 **Username Resolution**: Support for Telegram usernames and the 'me' entity for easier chat identification

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

## Usage

Rename the `sample.env` file to `.env` and modify the variables.

Run `sh run.sh` or `run.bat` to start the script.

> **Note:** You can run the script directly using `python summarize.py ...` as shown in the examples throughout this document, or you can use the helper scripts with arguments: `sh run.sh --chats John Sally` or `run.bat --chats John Sally`. The helper scripts create a virtual environment, install dependencies, and then run the summarize.py script with your provided arguments.

### Command Line Arguments

The script supports the following command line arguments:

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

#### Running with Templates

You can run the script using chat names and prompt templates:
```
# Using chat names
python summarize.py --chats John --send=TeamChat

# Using a prompt template
python summarize.py --chats John --prompt_template Technical

# Using multiple prompt templates (they will be combined)
python summarize.py --chats John --prompt_template Technical,Meeting

# Using a topic-specific chat defined in Templates.txt (avoids command line issues with underscores)
python summarize.py --chats ProjectTopic
```

**Tip:** Using Templates.txt is the recommended way to work with topic-specific chats, as it avoids the command line parsing issues with underscores.

#### Using Job Templates

Job templates allow you to store complete command configurations in the Templates.txt file and run them with a single command. This is especially useful for recurring tasks like daily or weekly summaries.

To create a job template, add a line with the `job:` prefix followed by the job name and the complete command line arguments:

```
job:JobName=--argument1 value1 --argument2 value2 ...
```

For example:
```
job:DailyUpdate=--chats John --send TeamChat --days 1 --prompt_template Daily
job:WeeklyReport=--chats John,ProjectDiscussion --send TeamChat --days 7 --prompt_template Weekly --debug
job:TechnicalSummary=--chats=-1001234567_789 --send=-1009876543 --prompt_template Technical
```

To run a job template, use the `--job` argument:
```bash
python summarize.py --job DailyUpdate
```

You can also run multiple job templates in a single command:
```bash
# Run multiple job templates (comma-separated)
python summarize.py --job DailyUpdate,WeeklyReport

# Run multiple job templates (separate arguments)
python summarize.py --job DailyUpdate WeeklyReport
```

This will execute the script with all the arguments defined in each job template, processing them sequentially. Job templates can include any valid command line arguments, including multiple chats, send targets, prompt templates, and flags like `--debug` or `--mock`.

**Important Notes about CLI Flags with Job Templates**:

**Debug Mode**:
- When debug mode is enabled via the command line (`--debug`), logs will only be shown in the console and not saved to any log file.
- If you specify `--debug` in a job template definition, but not on the command line, logs will still be saved to a log file.
- To ensure logs are only shown in the console when running a job, use `--debug` on the command line: `python summarize.py --job DailyUpdate --debug`

**CLI Flag Precedence**:
- Command line flags like `--debug` and `--mock` take precedence over job template settings.
- If you run `python summarize.py --job DailyUpdate --mock`, the mock mode will be enabled even if not specified in the job template.
- This allows you to test job templates with mock mode or enable debug output without modifying the job template definition.

## Configuration

### Environment Variables

The script uses a `.env` file for configuration. You can copy the `sample.env` file and modify it with your own values:

```bash
cp sample.env .env
```

Required environment variables:

| Variable | Description |
|----------|-------------|
| `TELEGRAM_API_ID` | Your Telegram API ID (get from https://my.telegram.org) |
| `TELEGRAM_API_HASH` | Your Telegram API hash (get from https://my.telegram.org) |
| `LLM_PROVIDER` | The LLM provider to use (e.g., "openai", "anthropic", "groq") |
| `LLM_MODEL` | The model to use (e.g., "gpt-4o-mini", "claude-2") |
| `LLM_API_KEY` | Your API key for the LLM provider |

Optional environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `PROMPT_SYSTEM` | System prompt for the AI | "You are a helpful summarizing assistant." |
| `PROMPT_TEXT` | Base user prompt for the AI | "Please summarize the conversations." |
| `PROXY` | Proxy URL for pip installations | None |

### Logging

The script creates detailed logs in the `logs` directory. Each run generates a timestamped log file with debug information, even when not running in debug mode.

## Dependencies

The script requires the following main dependencies:
- `python-dotenv`: For loading environment variables
- `telethon`: For interacting with Telegram
- `litellm`: For communicating with various LLM providers
- `rich`: For pretty console output
- `loguru`: For comprehensive logging

All dependencies are automatically installed when running the script with `run.sh` or `run.bat`.

## Advanced Usage

### Using Helper Scripts

Remember that all examples in this document can be run using the helper scripts instead of calling Python directly:

```bash
# Instead of
python summarize.py --chats John --days=5

# You can use
sh run.sh --chats John --days=5
# or on Windows
run.bat --chats John --days=5
```

The helper scripts handle setting up the virtual environment and installing dependencies, which is especially useful when running the script for the first time or on a new machine.

### Testing with Mock Mode

You can test the script without making actual API calls to LLM providers by using the `--mock` flag:

```bash
python summarize.py --chats John --mock
```

This will use a predefined mock response instead of calling the LLM API, which is useful for testing the workflow without incurring API costs.

### Combining Multiple Chats

You can summarize messages from multiple chats at once:

```bash
# Using comma-separated values
python summarize.py --chats John,Alice,TeamChat

# Using multiple arguments
python summarize.py --chats John Alice TeamChat
```

### Customizing Prompts

You can customize the AI prompt in several ways:

1. Using the `--prompt` argument for one-time instructions:
   ```bash
   python summarize.py --chats John --prompt="Focus on decisions made and action items"
   ```

2. Using predefined templates from Templates.txt:
   ```bash
   python summarize.py --chats John --prompt_template Technical
   ```

3. Combining multiple templates:
   ```bash
   python summarize.py --chats John --prompt_template Technical,Meeting
   ```

4. Overriding default prompts in Templates.txt:
   ```
   prompt:PROMPT_SYSTEM=Your custom system prompt
   prompt:PROMPT_TEXT=Your custom user prompt
   ```

## Troubleshooting

### Common Issues

1. **Authentication Error**: Make sure your `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` are correct in the `.env` file.

2. **Chat ID Not Found**: Verify that the chat ID is correct and that you have access to the chat. Try using a chat name from Templates.txt instead.

3. **LLM API Error**: Check that your `LLM_API_KEY`, `LLM_PROVIDER`, and `LLM_MODEL` are correctly set in the `.env` file.

4. **No Messages Found**: Make sure the chat has messages within the specified time range. Try increasing the `--days` parameter.

5. **Error with Topic-Specific Chat IDs**: When using chat IDs with underscores (for topic-specific chats), you must use the equals sign format:
   ```bash
   # CORRECT:
   python summarize.py --chats=-1001234567_789

   # INCORRECT:
   python summarize.py --chats -1001234567_789
   ```
   This is because the command line parser treats the underscore as a special character when it's not part of a quoted string or directly attached to the argument name.

### Debug Mode

For detailed information about what's happening, use the `--debug` flag:

```bash
python summarize.py --chats John --debug
```

This will display additional information in the console, including token usage, cost, and response time. When debug mode is enabled, logs will only be shown in the console and not saved to any log file.

### Logs

Check the `logs` directory for detailed logs of each run. The logs include all debug information when not running in debug mode. When debug mode is enabled (`--debug` flag), logs are only shown in the console and not saved to any log file.

## Setting Up Cron Jobs

You can automate the script to run at scheduled intervals using cron jobs. Here's how to set it up properly:

### 1. Make sure the script has proper permissions

```bash
# Navigate to your script directory
cd /path/to/telegram-summarizer

# Make sure run.sh is executable
chmod +x run.sh
```

### 2. Create or edit your crontab

```bash
crontab -e
```

### 3. Add a cron entry with proper paths and output redirection

```
# Format: minute hour day month weekday command
# Example: Run daily at 8:00 AM
0 8 * * * cd /full/path/to/telegram-summarizer && ./run.sh --chats ChatName --send TargetChat --prompt_template TemplateName >> logs/cron.log 2>&1
```

### Important Notes for Cron Jobs:

1. **Always use full paths** in your cron entries to avoid path-related issues
2. **Redirect output** with `>> logs/cron.log 2>&1` to capture both standard output and errors
3. **Change directory** with `cd` before running the script to ensure proper relative path resolution
4. **Test your cron job** with a more frequent schedule before setting it to your desired interval
5. **Check the log file** after the scheduled time to verify the job ran successfully

### Example Cron Entries:

```
# Run telegram summarizer daily at 8:00 AM with explicit arguments
0 8 * * * cd /Users/username/Documents/git/telegram-summarizer && ./run.sh --chats John,Sally --days 0 --send TeamChat --prompt_template Meeting >> logs/cron.log 2>&1

# Run telegram summarizer using a job template (recommended for complex configurations)
0 8 * * * cd /Users/username/Documents/git/telegram-summarizer && ./run.sh --job DailyUpdate >> logs/cron.log 2>&1

# Run multiple job templates in sequence
0 8 * * * cd /Users/username/Documents/git/telegram-summarizer && ./run.sh --job DailyUpdate,WeeklyReport >> logs/cron.log 2>&1

# Run different job templates at different times
0 8 * * 1-5 cd /Users/username/Documents/git/telegram-summarizer && ./run.sh --job DailyUpdate >> logs/cron.log 2>&1
0 9 * * 0 cd /Users/username/Documents/git/telegram-summarizer && ./run.sh --job WeeklyReport >> logs/cron.log 2>&1
```

### Troubleshooting Cron Issues:

- **Permission denied errors**: Make sure run.sh is executable (`chmod +x run.sh`)
- **Command not found errors**: Use full paths to all commands and scripts
- **Environment variables missing**: Set necessary environment variables in the cron entry
- **macOS permissions**: On newer macOS versions, grant Full Disk Access to cron in System Preferences > Security & Privacy > Privacy

### Using launchd on macOS (Alternative to Cron)

On macOS, Apple recommends using `launchd` instead of cron for scheduling tasks. Here's how to set it up:

1. **Create a plist file** (e.g., `com.username.telegramsummarizer.plist`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.username.telegramsummarizer</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/full/path/to/telegram-summarizer/run.sh</string>
        <string>--job</string>
        <string>DailyUpdate</string>
    </array>
    <!-- Alternative with explicit arguments:
    <array>
        <string>/bin/bash</string>
        <string>/full/path/to/telegram-summarizer/run.sh</string>
        <string>--chats</string>
        <string>ChatName</string>
        <string>--send</string>
        <string>TargetChat</string>
    </array>
    -->
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/full/path/to/telegram-summarizer/logs/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>/full/path/to/telegram-summarizer/logs/launchd_error.log</string>
    <key>WorkingDirectory</key>
    <string>/full/path/to/telegram-summarizer</string>
</dict>
</plist>
```

2. **Install the launchd job**:

```bash
# Copy the plist file to the LaunchAgents directory
cp com.username.telegramsummarizer.plist ~/Library/LaunchAgents/

# Load the job
launchctl load ~/Library/LaunchAgents/com.username.telegramsummarizer.plist
```

3. **Test the job**:

```bash
launchctl start com.username.telegramsummarizer
```

4. **Check the logs** in the specified log files to verify it worked.


## Future Improvements

- [ ] Add support for schedules from the command line and single entry point for cron jobs
- [x] Add support for Job templates, which can be used to run the script with predefined arguments
- [ ] Test with other LLM providers
- [ ] Add support for more Telegram message types (e.g., photos, videos)
- [ ] Implement caching to avoid redundant API calls
- [ ] Allow to send message as a different entity, eg. as a group the user owns/manages
- [ ] Add more options for the output of generated content, including `file`, `webhook`, and `console` (console will not print anything else to the console except the generated content)
- [ ] Add support for filtering messages by user or keyword
- [ ] Implement message deduplication for cross-posted content
- [ ] Add support for custom formatting of the summary output
- [x] Support for Telegram usernames and the 'me' entity for easier chat identification

