import argparse
import os
import sys
import asyncio
import time
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telethon import TelegramClient
import litellm
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TimeElapsedColumn, TaskProgressColumn
from rich.live import Live
from rich.table import Table
from loguru import logger

# Initialize Rich console for the main block
console = Console()


def read_templates_file():
    """Read the Templates.txt file and return dictionaries for chat IDs and prompt templates"""
    chat_templates = {}
    prompt_templates = {}
    job_templates = {}

    try:
        if os.path.isfile('Templates.txt'):
            with open('Templates.txt', 'r') as f:
                for line in f:
                    # Skip comments and empty lines
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    # Parse key-value pairs
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()

                        if key.startswith('chat:') and value:
                            # Extract chat name without the prefix
                            chat_name = key[5:]
                            chat_templates[chat_name] = value
                            logger.debug(f"Loaded chat template: {chat_name} -> {value}")
                        elif key.startswith('prompt:') and value:
                            # Extract prompt name without the prefix
                            prompt_name = key[7:]
                            prompt_templates[prompt_name] = value
                            logger.debug(f"Loaded prompt template: {prompt_name}")
                        elif key.startswith('job:') and value:
                            # Extract job name without the prefix
                            job_name = key[4:]
                            job_templates[job_name] = value
                            logger.debug(f"Loaded job template: {job_name}")

            logger.debug(f"Loaded {len(chat_templates)} chat entries and {len(prompt_templates)} prompt templates from Templates.txt")
        else:
            logger.warning("Templates.txt file not found")
    except Exception as e:
        logger.error(f"Error reading Templates.txt: {str(e)}")

    return chat_templates, prompt_templates, job_templates


def resolve_chat_id(chat_arg, chat_templates):
    """Resolve a chat ID or name to a numeric chat ID"""
    # Handle potential escaping of underscores in command line arguments
    chat_arg = chat_arg.replace('\\\_', '_')

    # If it's already a chat ID format (number or number with underscore), return it as is
    # This pattern matches:
    # 1. Regular numbers with optional negative sign
    # 2. Numbers with underscores (like -100123456_789)
    if re.match(r'^-?\d+(_\d+)?$', chat_arg):
        logger.debug(f"Recognized '{chat_arg}' as a chat ID format")
        return chat_arg

    # Otherwise, look it up in the chat templates
    if chat_arg in chat_templates:
        logger.debug(f"Resolved chat name '{chat_arg}' to ID '{chat_templates[chat_arg]}'")
        return chat_templates[chat_arg]

    # If not found, return None
    logger.error(f"Chat name '{chat_arg}' not found in Templates.txt")
    return None


def resolve_prompt_template(template_name, prompt_templates):
    """Resolve a prompt template name to the actual template text"""
    if template_name in prompt_templates:
        logger.debug(f"Using prompt template '{template_name}'")
        return prompt_templates[template_name]

    # If not found, return None
    logger.error(f"Prompt template '{template_name}' not found in Templates.txt")
    return None


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description='Telegram Chat Summarizer - Summarize messages from multiple Telegram chats using AI.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    # Summarize messages from two chats (comma-separated) and send to another chat
    python summarize.py --chats -1001234567,-1009876543 --send=-1001122334 --days=3

    # Summarize messages from two chats (separate arguments) and send to another chat
    python summarize.py --chats -1001234567 -1009876543 --send=-1001122334 --days=3

    # Add custom instructions to the AI prompt
    python summarize.py --chats -1001234567 --send=-1001122334 --prompt="Focus on technical discussions"

    # Use a predefined prompt template from Templates.txt
    python summarize.py --chats -1001234567 --send=-1001122334 --prompt_template Technical

    # Summarize messages and display in console only (no Telegram sending)
    python summarize.py --chats -1001234567 --days=3

    # Use chat names from Templates.txt instead of numeric IDs
    python summarize.py --chats John --send=TeamChat --days=3

    # Enable debug mode to see detailed information about the LLM response
    python summarize.py --chats -1001234567 --debug

    # Use mock mode to test without actually calling the LLM API
    python summarize.py --chats -1001234567 --mock

Note:
    - Chat IDs usually start with -100 for groups/channels
    - Chat IDs with underscores (e.g., -1001234567_789) are supported for topic-specific chats
    - You can get chat IDs by forwarding a message to @username_to_id_bot
    - You can use chat names from the Templates.txt file instead of numeric IDs (e.g., "John" instead of "-1001234567890")
    - You can use prompt templates from Templates.txt to use predefined prompts (e.g., "Technical" for technical summaries)
    - Special templates "PROMPT_SYSTEM" and "PROMPT_TEXT" will override environment variables if present in Templates.txt
    - Ensure your .env file contains TELEGRAM_API_ID, TELEGRAM_API_HASH, and LLM configuration
    ''')

    parser.add_argument('--chats',
                      help='Chat IDs or names from Templates.txt to summarize from (can be comma-separated or multiple values)',
                      required=False,
                      nargs='*',
                      type=str,
                      default=[])

    parser.add_argument('--send',
                      help='Chat IDs or names from Templates.txt where the summary should be sent (can be comma-separated or multiple values)',
                      required=False,
                      nargs='*',
                      type=str,
                      default=[])

    parser.add_argument('--days',
                      help='Number of days to look back (default: 3)',
                      type=int,
                      default=3)

    parser.add_argument('--prompt',
                      help='Additional instructions for the AI summarizer',
                      default='')

    parser.add_argument('--prompt_template',
                      help='Name of a prompt template from Templates.txt to use instead of the default prompt',
                      nargs='*',
                      default=[])

    parser.add_argument('--debug',
                      help='Enable debug mode',
                      action='store_true')

    parser.add_argument('--mock',
                      help='Use mock response instead of calling the LLM API',
                      action='store_true')
    
    parser.add_argument('--job',
                      help='Name of a job template from Templates.txt to use instead of the default prompt',
                      default='')

    args, unkown = parser.parse_known_args(args)
    
    # if no arguments are passed, then we stop the script here.
    if not any(vars(args).values()) and not args.job:
        parser.print_help()
        sys.exit(1)

    # Special handling for chat IDs with underscores
    if args.chats:
        # Process each chat ID to handle potential escaping issues with underscores
        processed_chats = []
        for chat in args.chats:
            # Replace any escaped underscores with regular underscores
            processed_chat = chat.replace('\\\_', '_').replace('\\_', '_')
            processed_chats.append(processed_chat)
        args.chats = processed_chats

    if args.send:
        # Process each send ID to handle potential escaping issues with underscores
        processed_send = []
        for send in args.send:
            # Replace any escaped underscores with regular underscores
            processed_send_id = send.replace('\\\_', '_').replace('\\_', '_')
            processed_send.append(processed_send_id)
        args.send = processed_send

    # Print chat IDs for debugging
    print(f"Processing chats: {args.chats}")

    return args

# Function removed as its functionality is now integrated directly into process_telegram_data

def check_env_file():
    """Check if .env file exists and load environment variables"""
    # Check if .env file exists
    if not os.path.isfile('.env'):
        error_text = Text("Error: .env file not found!", style="bold red")
        help_text = Text("\nPlease create a .env file with your configuration settings. You can use sample.env as a template:\n\n1. Copy sample.env to .env\n2. Fill in your Telegram API credentials and LLM settings\n\nCommand to copy the file: cp sample.env .env", style="yellow")

        console.print(Panel(
            error_text + help_text,
            title="Configuration Error",
            border_style="red",
            expand=False
        ))
        sys.exit(1)

    # Load environment variables
    load_dotenv(override=True)

    # Check required environment variables
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    llm_provider = os.getenv('LLM_PROVIDER')
    llm_model = os.getenv('LLM_MODEL')
    llm_api_key = os.getenv('LLM_API_KEY')

    if not all([api_id, api_hash, llm_provider, llm_model, llm_api_key]):
        error_text = Text("Missing required environment variables!", style="bold red")
        help_text = Text("\nPlease check your .env file and ensure it contains the following variables:\n\n- TELEGRAM_API_ID\n- TELEGRAM_API_HASH\n- LLM_PROVIDER\n- LLM_MODEL\n- LLM_API_KEY", style="yellow")

        console.print(Panel(
            error_text + help_text,
            title="Configuration Error",
            border_style="red",
            expand=False
        ))
        sys.exit(1)

    return {
        'api_id': api_id,
        'api_hash': api_hash,
        'llm_provider': llm_provider,
        'llm_model': llm_model,
        'llm_api_key': llm_api_key
    }

async def run_telegram_client(args, env_vars):
    """Initialize and run the Telegram client with the parsed arguments"""
    # Extract environment variables
    api_id = env_vars['api_id']
    api_hash = env_vars['api_hash']
    llm_provider = env_vars['llm_provider']
    llm_model = env_vars['llm_model']
    llm_api_key = env_vars['llm_api_key']

    console.print("[bold blue]Initializing Telegram client...[/bold blue]")

    # Initialize Telegram client
    client = TelegramClient('session_name', api_id, api_hash)

    try:
        console.print("[bold blue]Starting Telegram client...[/bold blue]")
        await client.start()
        console.print("[bold green]Telegram client started.[/bold green]")

        # Process the rest of the logic with the client
        await process_telegram_data(client, args, env_vars)
    finally:
        # Ensure client is disconnected
        await client.disconnect()

async def process_telegram_data(client, args, env_vars):
    """Process Telegram data and generate summary"""
    # Extract environment variables
    llm_provider = env_vars['llm_provider']
    llm_model = env_vars['llm_model']
    llm_api_key = env_vars['llm_api_key']

    # Prepare the base prompt
    console.print("[bold blue]Setting up...[/bold blue]")

    # Load the templates file
    chat_templates, prompt_templates, job_templates = read_templates_file()

    # Check if PROMPT_SYSTEM exists in prompt templates
    if 'PROMPT_SYSTEM' in prompt_templates:
        system_prompt = prompt_templates['PROMPT_SYSTEM']
        logger.debug("Using PROMPT_SYSTEM from Templates.txt")
    else:
        system_prompt = os.getenv('PROMPT_SYSTEM', 'You are a helpful summarizing assistant.')
        logger.debug("Using PROMPT_SYSTEM from environment variable or default")

    # Add today's date to the system prompt
    system_prompt = system_prompt + f". Today is {datetime.now().strftime('%Y-%m-%d')}."

    full_prompt = [
        {'role': 'system', 'content': system_prompt},
    ]

    # Fetch messages from all specified chats
    console.print("[bold blue]Preparing to fetch messages...[/bold blue]")

    # Process chat IDs - handle both comma-separated values and multiple arguments
    chat_ids = []
    for chat_arg in args.chats:
        # Check if this argument contains commas
        if ',' in chat_arg:
            # Split by comma and add each part
            for chat in chat_arg.split(','):
                if chat.strip():
                    # Resolve chat name to ID if needed
                    resolved_chat = resolve_chat_id(chat.strip(), chat_templates)
                    if resolved_chat:
                        # Handle chat IDs with underscores (e.g., -100123456_789)
                        if '_' in resolved_chat:
                            chat_ids.append(resolved_chat)
                            logger.debug(f"Added chat ID with underscore: {resolved_chat}")
                        else:
                            try:
                                chat_ids.append(int(resolved_chat))
                                logger.debug(f"Added numeric chat ID: {resolved_chat}")
                            except ValueError:
                                console.print(f"[bold red]Error: Invalid chat ID format for '{chat.strip()}' (resolved to '{resolved_chat}')[/bold red]")
                    else:
                        console.print(f"[bold red]Error: Chat '{chat.strip()}' not found in Templates.txt[/bold red]")
        else:
            # Resolve chat name to ID if needed
            resolved_chat = resolve_chat_id(chat_arg.strip(), chat_templates)
            if resolved_chat:
                # Handle chat IDs with underscores (e.g., -100123456_789)
                if '_' in resolved_chat:
                    chat_ids.append(resolved_chat)
                    logger.debug(f"Added chat ID with underscore: {resolved_chat}")
                else:
                    try:
                        chat_ids.append(int(resolved_chat))
                        logger.debug(f"Added numeric chat ID: {resolved_chat}")
                    except ValueError:
                        console.print(f"[bold red]Error: Invalid chat ID format for '{chat_arg.strip()}' (resolved to '{resolved_chat}')[/bold red]")
            else:
                console.print(f"[bold red]Error: Chat '{chat_arg.strip()}' not found in Templates.txt[/bold red]")

    # Create a single progress display for the entire process
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("•"),
        TimeElapsedColumn()
    ) as progress:
        # Add tasks for each stage
        overall_task = progress.add_task("[bold green]Overall Progress", total=100, completed=5)
        fetch_task = progress.add_task("[bold blue]Fetching messages", total=len(chat_ids), visible=False)

        # Update overall progress - 10%
        progress.update(overall_task, completed=10)

        # Make fetch task visible when we start fetching
        progress.update(fetch_task, visible=True)

        # Fetch messages from each chat
        for i, chat_id in enumerate(chat_ids):
            # Update task description
            progress.update(fetch_task, description=f"[bold blue]Fetching from chat {i+1}/{len(chat_ids)}")

            # Get channel information and log it to file
            try:
                # Handle chat IDs with underscores for entity retrieval
                entity_chat_id = chat_id
                thread_info = ""

                if isinstance(chat_id, str) and '_' in chat_id:
                    base_chat_id, thread_id = chat_id.split('_')
                    entity_chat_id = int(base_chat_id)
                    thread_info = f", Thread ID: {thread_id}"

                channel_entity = await client.get_entity(entity_chat_id)
                if hasattr(channel_entity, 'title'):
                    channel_name = channel_entity.title
                elif hasattr(channel_entity, 'first_name'):
                    channel_name = f"{channel_entity.first_name} {getattr(channel_entity, 'last_name', '')}"
                else:
                    channel_name = "Unknown"

                logger.debug(f"Channel info: {channel_name} (ID: {chat_id}{thread_info})")
            except Exception as e:
                logger.error(f"Error getting channel info: {str(e)}")

            # Calculate midnight of args.days ago
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            offset_date = today - timedelta(days=args.days)

            # Always log time range to file
            logger.debug(f"Fetching messages from chat {chat_id} from {offset_date} to now")
            logger.debug(f"Time range: {offset_date.strftime('%Y-%m-%d %H:%M')} to {datetime.now().strftime('%Y-%m-%d %H:%M')}")

            # Count messages
            logger.debug(f"Counting messages from channel ID: {chat_id}")
            total_messages = 0

            # Handle message_thread_id if chat_id contains underscore for counting
            count_message_thread_id = None
            count_chat_id = chat_id

            if isinstance(chat_id, str) and '_' in chat_id:
                count_base_chat_id, count_thread_id = chat_id.split('_')
                count_message_thread_id = int(count_thread_id)
                count_chat_id = int(count_base_chat_id)
                logger.debug(f"Counting messages from topic: base chat ID {count_base_chat_id}, thread ID {count_thread_id}")

            # Use message_thread_id parameter if it's a topic-specific chat
            async for _ in client.iter_messages(
                count_chat_id,
                offset_date=offset_date,
                reverse=True,
                reply_to=count_message_thread_id
            ):
                total_messages += 1
                if total_messages % 100 == 0:
                    logger.debug(f"Counted {total_messages} messages so far from chat {chat_id}")

            if total_messages == 0:
                msg = f"No messages found in channel {chat_id} since {offset_date.strftime('%Y-%m-%d')}"
                console.print(f"[bold yellow]{msg}[/bold yellow]")
                if args.debug:
                    logger.warning(msg)
                progress.update(fetch_task, advance=1)
                continue

            logger.info(f"Fetching {total_messages} messages from channel ID: {chat_id}")

            # Add a task for message fetching with channel name if available
            channel_name_display = f"{channel_name}" if 'channel_name' in locals() else f"{chat_id}"
            message_task = progress.add_task(f"[cyan]Messages from {channel_name_display}", total=total_messages)

            # Fetch messages
            messages = []
            count = 0
            last_messages = []  # Store the last 3 messages for debug output

            # Handle message_thread_id if chat_id contains underscore
            message_thread_id = None
            chat_id_for_fetching = chat_id

            if isinstance(chat_id, str) and '_' in chat_id:
                base_chat_id, thread_id = chat_id.split('_')
                message_thread_id = int(thread_id)
                chat_id_for_fetching = int(base_chat_id)
                logger.debug(f"Fetching from topic: base chat ID {base_chat_id}, thread ID {thread_id}")

            # Use message_thread_id parameter if it's a topic-specific chat
            async for message in client.iter_messages(
                chat_id_for_fetching,
                offset_date=offset_date,
                reverse=True,
                reply_to=message_thread_id
            ):
                # Format the message with date, sender, and text
                message_date = message.date.strftime("%Y-%m-%d %H:%M:%S")

                if message.text and len(message.text) > 1 :  # Only process messages with text content
                    if message.is_group:
                        sender = await message.get_sender()
                        sender_name = sender.first_name if sender and hasattr(sender, 'first_name') else "Unknown"
                        formatted_message = f"{message_date}:{sender_name}:{message.text}"
                    else:
                        formatted_message = f"{message_date}:{message.text}"

                    messages.append(formatted_message)

                    # Keep track of the last 3 messages for debug output
                    if len(last_messages) >= 3:
                        last_messages.pop(0)
                    last_messages.append(formatted_message)

                    # Always log messages to file
                    # Replace actual line breaks with \n escape sequence for logging
                    log_message = formatted_message.replace("\n", "\\n")
                    logger.debug(f"Message from {chat_id}: {log_message[:100]}..." if len(log_message) > 100 else log_message)

                count += 1
                progress.update(message_task, completed=count)

                # No delay needed

            # Ensure the progress bar reaches 100%
            if count < total_messages:
                progress.update(message_task, completed=total_messages)

            # Add messages to prompt
            message_text = "\n".join(messages)

            # Log the last 3 messages but don't print to console
            if messages:
                logger.debug(f"Added {len(messages)} messages from chat {chat_id} to the prompt")
                # Format last messages with escaped newlines
                formatted_last_messages = [msg.replace("\n", "\\n") for msg in last_messages[-3:]]
                logger.debug(f"Last 3 messages: {formatted_last_messages}")

            # Check if we have any messages to add
            if messages:
                full_prompt.append({'role': 'user', 'content': message_text})
                logger.debug(f"Added content from chat {chat_id} to prompt (length: {len(message_text)} chars)")
            else:
                logger.warning(f"No text messages found in chat {chat_id}, skipping")
                console.print(f"[bold yellow]No text messages found in chat {chat_id}, skipping[/bold yellow]")

            # Update fetch progress
            progress.update(fetch_task, advance=1)

            # Update overall progress (allocate 40% to fetching, divided among chats)
            fetch_percent = 40 / len(chat_ids)
            current_overall = 10 + fetch_percent * (i + 1)
            progress.update(overall_task, completed=min(50, current_overall))

            # Remove the message task when done
            progress.remove_task(message_task)

        # Update fetch task to show completion
        progress.update(fetch_task, completed=len(chat_ids))
        # Hide fetch task when done
        progress.update(fetch_task, visible=False)

        # Update overall progress - 50%
        progress.update(overall_task, completed=50, description="[bold blue]Preparing prompt for AI...")

        # Get the base prompt text (prioritize Templates.txt over environment variables)
        base_prompt = None

        # First check if PROMPT_TEXT exists in prompt templates
        if 'PROMPT_TEXT' in prompt_templates:
            base_prompt = prompt_templates['PROMPT_TEXT']
            logger.debug("Using PROMPT_TEXT from Templates.txt")
        else:
            # If not in Templates.txt, check environment variable
            base_prompt = os.getenv('PROMPT_TEXT', 'Please summarize the conversations.')
            logger.debug("Using PROMPT_TEXT from environment variable or default")

        # Check if prompt templates are specified via command line
        if args.prompt_template:
            # Process prompt templates - handle both comma-separated values and multiple arguments
            prompt_texts = []
            for template_arg in args.prompt_template:
                # Check if this argument contains commas
                if ',' in template_arg:
                    # Split by comma and add each part
                    for template in template_arg.split(','):
                        if template.strip():
                            # Resolve template name to text
                            resolved_template = resolve_prompt_template(template.strip(), prompt_templates)
                            if resolved_template:
                                prompt_texts.append(resolved_template)
                            else:
                                console.print(f"[bold yellow]Warning: Prompt template '{template.strip()}' not found in Templates.txt, skipping[/bold yellow]")
                else:
                    # Resolve template name to text
                    resolved_template = resolve_prompt_template(template_arg.strip(), prompt_templates)
                    if resolved_template:
                        prompt_texts.append(resolved_template)
                    else:
                        console.print(f"[bold yellow]Warning: Prompt template '{template_arg.strip()}' not found in Templates.txt, skipping[/bold yellow]")

            # Combine all prompt templates with the custom prompt
            if prompt_texts:
                combined_template = " ".join(prompt_texts)
                full_prompt_text = f"{combined_template} {args.prompt}".strip()
                logger.debug(f"Using prompt templates: {', '.join(args.prompt_template)}")
            else:
                # Fall back to the base prompt if no templates were found
                full_prompt_text = f"{base_prompt} {args.prompt}".strip()
                logger.debug("No valid prompt templates found, using base prompt")
        else:
            # Use the base prompt
            full_prompt_text = f"{base_prompt} {args.prompt}".strip()

        # Add the final prompt to the messages
        full_prompt.append({'role': 'user', 'content': full_prompt_text})

        # Always log final instruction to file
        logger.debug(f"Added final instruction to prompt: {full_prompt_text}")

        # Check if we have any actual content in the prompt
        content_messages = [msg for msg in full_prompt if msg['role'] == 'user' and len(msg['content']) > 0]
        if len(content_messages) <= 1:  # Only the instruction, no chat content
            logger.warning("No chat content was added to the prompt! The summary may fail.")
            console.print("\n[bold red]Warning: No chat content was added to the prompt![/bold red]")
            # Stop the script here
            sys.exit(1)

        # Update overall progress - 60%
        progress.update(overall_task, completed=60, description=f"[bold blue]Initializing LiteLLM with {llm_provider}/{llm_model}...")

        # Initialize LiteLLM
        litellm.api_key = llm_api_key

        # Update overall progress - 70%
        progress.update(overall_task, completed=70, description="[bold blue]Generating summary with AI...")

        # Start time for estimation
        start_time = time.time()

        # Add AI processing task
        ai_task = progress.add_task("[yellow]AI Processing", total=None)

        # Always log token usage to file
        # Calculate approximate token count for input
        total_chars = sum(len(msg.get('content', '')) for msg in full_prompt)
        approx_tokens = total_chars / 4  # Rough estimate: ~4 chars per token

        logger.debug(f"Sending prompt to LLM: {len(full_prompt)} messages, ~{total_chars:,} characters, ~{int(approx_tokens):,} tokens")

        # Log the full prompt structure
        for i, msg in enumerate(full_prompt):
            # Replace newlines with escape sequences
            content = msg['content'].replace("\n", "\\n")
            content_preview = content[:1000] + "..." if len(content) > 1000 else content
            logger.debug(f"Prompt message {i+1} ({msg['role']}): {content_preview}")

        # Get response from LLM or use mock
        try:
            if args.mock:
                # Create a mock response content
                mock_content = f"""
Here is a summary of the conversations from the Telegram chats:

The discussions over the past {args.days} days primarily focused on several key topics:

1. **Project Updates**: Team members shared progress on the current sprint, with most tasks on track for completion by the end of the week.

2. **Technical Discussions**: There were detailed conversations about implementing the new API endpoints and resolving the database performance issues.

3. **Community Feedback**: Users reported positive experiences with the latest release, though some minor UI issues were noted.

4. **Upcoming Features**: The team discussed prioritizing the notification system improvements and the new dashboard for the next release.

Several action items were identified:
- Complete code reviews by Thursday
- Schedule a meeting to address the reported UI issues
- Finalize the documentation for the new features

This summary covers the main points of discussion. For more detailed information on specific topics, please refer to the full conversation history.
"""
                console.print("[bold yellow]Using mock response (no API call will be made)[/bold yellow]")
                logger.info("Using mock response instead of calling LLM API")
                # Replace newlines with escape sequences for logging
                escaped_mock = mock_content.replace("\n", "\\n")

                # Use LiteLLM's built-in mock_response parameter
                response = litellm.completion(
                    messages=full_prompt,
                    model=f"{llm_provider}/{llm_model}",
                    mock_response=mock_content
                )
            else:
                logger.info(f"Sending request to {llm_provider}/{llm_model}")
                response = litellm.completion(messages=full_prompt, model=f"{llm_provider}/{llm_model}")

            # Always log response to file
            response_content = response.choices[0].message.content.replace("\n", "\\n")
            logger.debug(f"Raw response content: {response_content}")
        except Exception as e:
            error_msg = f"Error calling LLM API: {str(e)}"
            logger.error(error_msg)
            console.print(f"[bold red]{error_msg}[/bold red]")
            raise

        # Calculate time taken
        time_taken = time.time() - start_time

        # Update overall progress to reflect AI completion
        progress.update(overall_task, completed=80, description="[bold blue]AI processing complete!")

        # Remove the AI task
        progress.remove_task(ai_task)
        console.print(f"[bold green]Summary generated in [/bold green][cyan]{time_taken:.2f}s[/cyan]")

        # Always log summary generation time and token usage to file
        logger.info(f"Summary generated in {time_taken:.2f}s")

        # Log the full response object for debugging
        logger.debug(f"Full response object: {response}")
        logger.debug(f"Response hidden params: {response._hidden_params}")

        # Log token usage and cost
        # Check if we're using mock mode
        if args.mock:
            # Simulate token counts based on string length when using mock
            # Rough estimate: ~4 chars per token for prompt, ~2.5 chars per token for completion
            prompt_chars = sum(len(msg.get('content', '')) for msg in full_prompt)
            completion_chars = len(response.choices[0].message.content)

            prompt_tokens = int(prompt_chars / 4)  # Simulate prompt tokens
            completion_tokens = int(completion_chars / 2.5)  # Simulate completion tokens
            total_tokens = prompt_tokens + completion_tokens

            # Simulate cost based on token count (using typical GPT-4 rates)
            prompt_cost = prompt_tokens * 0.00001  # $0.01 per 1000 tokens
            completion_cost = completion_tokens * 0.00003  # $0.03 per 1000 tokens
            raw_cost = prompt_cost + completion_cost
        else:
            # Extract token usage from the response object's usage field
            if hasattr(response, 'usage') and response.usage:
                prompt_tokens = getattr(response.usage, 'prompt_tokens', 'N/A')
                completion_tokens = getattr(response.usage, 'completion_tokens', 'N/A')
                total_tokens = getattr(response.usage, 'total_tokens', 'N/A')
            else:
                # Fallback to _hidden_params if usage is not available
                prompt_tokens = response._hidden_params.get('prompt_tokens', 'N/A')
                completion_tokens = response._hidden_params.get('completion_tokens', 'N/A')
                total_tokens = response._hidden_params.get('total_tokens', 'N/A')

            # Get cost from response if available
            raw_cost = response._hidden_params.get('response_cost', 0)

        # Format the cost with 5 decimal places
        formatted_cost = f"{float(raw_cost):.5f}" if isinstance(raw_cost, (int, float)) else 'N/A'

        logger.debug(f"Token usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")
        logger.debug(f"Cost: ${formatted_cost}")

        # Log the summary with escaped newlines
        summary_content = response.choices[0].message.content.replace("\n", "\\n")
        logger.debug(f"AI Response: {summary_content}")

        # Check if we need to send to Telegram
        send_ids = []
        for send_arg in args.send:
            # Check if this argument contains commas
            if ',' in send_arg:
                # Split by comma and add each part
                for chat in send_arg.split(','):
                    if chat.strip():
                        # Resolve chat name to ID if needed
                        resolved_chat = resolve_chat_id(chat.strip(), chat_templates)
                        if resolved_chat:
                            # Handle chat IDs with underscores (e.g., -100123456_789)
                            if '_' in resolved_chat:
                                send_ids.append(resolved_chat)
                                logger.debug(f"Added send target with underscore: {resolved_chat}")
                            else:
                                try:
                                    send_ids.append(int(resolved_chat))
                                    logger.debug(f"Added numeric send target: {resolved_chat}")
                                except ValueError:
                                    console.print(f"[bold red]Error: Invalid chat ID format for send target '{chat.strip()}' (resolved to '{resolved_chat}')[/bold red]")
                        else:
                            console.print(f"[bold red]Error: Send target '{chat.strip()}' not found in Templates.txt[/bold red]")
            else:
                # Resolve chat name to ID if needed
                resolved_chat = resolve_chat_id(send_arg.strip(), chat_templates)
                if resolved_chat:
                    # Handle chat IDs with underscores (e.g., -100123456_789)
                    if '_' in resolved_chat:
                        send_ids.append(resolved_chat)
                        logger.debug(f"Added send target with underscore: {resolved_chat}")
                    else:
                        try:
                            send_ids.append(int(resolved_chat))
                            logger.debug(f"Added numeric send target: {resolved_chat}")
                        except ValueError:
                            console.print(f"[bold red]Error: Invalid chat ID format for send target '{send_arg.strip()}' (resolved to '{resolved_chat}')[/bold red]")
                else:
                    console.print(f"[bold red]Error: Send target '{send_arg.strip()}' not found in Templates.txt[/bold red]")

        if send_ids:
            # Update overall progress - 90%
            progress.update(overall_task, completed=90, description="[bold blue]Sending summary to Telegram...")

            # Add sending task
            send_task = progress.add_task("[cyan]Sending to Telegram", total=len(send_ids))

            # Send response to the specified channel(s)
            for i, send_id in enumerate(send_ids):
                logger.info(f"Sending summary to Telegram chat ID: {send_id}")

                # Update task description to show current chat ID
                progress.update(send_task, description=f"[cyan]Sending to chat {send_id} ({i+1}/{len(send_ids)})")

                # Handle message_thread_id if chat_id contains underscore
                message_thread_id = None
                chat_id_for_sending = send_id

                if isinstance(send_id, str) and '_' in send_id:
                    base_chat_id, thread_id = send_id.split('_')
                    message_thread_id = int(thread_id)
                    chat_id_for_sending = base_chat_id
                    logger.debug(f"Sending to topic: base chat ID {base_chat_id}, thread ID {thread_id}")

                try:
                    # First get the entity
                    entity = await client.get_entity(int(chat_id_for_sending))
                    await client.send_message(entity, response.choices[0].message.content, reply_to=message_thread_id)
                    console.print(f"[bold green]Summary sent to Telegram chat ID: [/bold green][yellow]{send_id}[/yellow]")
                    logger.info(f"Summary successfully sent to Telegram chat ID: {send_id}")
                except Exception as e:
                    error_msg = f"Error sending message to {send_id}: {str(e)}"
                    logger.error(error_msg)
                    console.print(f"[bold red]{error_msg}[/bold red]")

                progress.update(send_task, advance=1)

            # Remove sending task
            progress.remove_task(send_task)
        else:
            # Update overall progress - 90%
            progress.update(overall_task, completed=90, description="[bold blue]Preparing final output...")
            logger.info("No Telegram chat IDs provided for sending, displaying summary in console only")

        # Update overall progress - 100%
        progress.update(overall_task, completed=100, description="[bold green]Summary process completed!")
        logger.info("Summary process completed successfully")

    # Final confirmation message
    if send_ids:
        success_message = "Summary successfully generated and sent to Telegram!"
    else:
        success_message = "Summary successfully generated!"

    console.print(Panel(
        Text(success_message, style="bold green"),
        title="Process Complete",
        border_style="green"
    ))

    # Always display the summary in the console
    console.print(Panel(
        Text(response.choices[0].message.content, style="white"),
        title="Generated Summary",
        border_style="blue"
    ))

    # We already have the token usage and cost from earlier, just use those values
    # The response_time is the time_taken we calculated
    response_time = time_taken

    # Add mock mode indicator if applicable
    mock_indicator = " [dim](simulated)[/dim]" if args.mock else ""
    mock_indicator_bold = "[bold red](MOCK RESPONSE)[/bold red] " if args.mock else ""

    # Always display cost and token information
    console.print(f"[bold blue]Completion Cost: [/bold blue][green]${formatted_cost}{mock_indicator}[/green]")
    console.print(f"[bold blue]Tokens: [/bold blue][green]Prompt: {prompt_tokens} | Completion: {completion_tokens} | Total: {total_tokens}{mock_indicator}[/green]")
    console.print(f"[bold blue]Response Time: [/bold blue][green]{response_time:.2f}s[/green]")

    # Display additional debug information if debug mode is enabled
    if args.debug:
        cost_indicator = " (simulated)" if args.mock else ""
        debug_panel = Panel(
            Text.from_markup(
                f"[bold]Debug Information:[/bold]\n\n"
                f"[yellow]Provider:[/yellow] {llm_provider} {mock_indicator_bold}\n"
                f"[yellow]Model:[/yellow] {llm_model}\n"
                f"[yellow]Prompt Tokens:[/yellow] {prompt_tokens}\n"
                f"[yellow]Completion Tokens:[/yellow] {completion_tokens}\n"
                f"[yellow]Total Tokens:[/yellow] {total_tokens}\n"
                f"[yellow]Cost:[/yellow] ${formatted_cost}{cost_indicator}\n"
                f"[yellow]Response Time:[/yellow] {response_time:.2f}s\n"
                f"[yellow]Log Directory:[/yellow] ./logs/\n"
            ),
            title=f"{'Mock ' if args.mock else ''}LLM Response Details",
            border_style="yellow"
        )
        console.print(debug_panel)

def setup_logging():
    """Set up logging configuration with a logs directory"""
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.getcwd(), "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        print(f"Created logs directory: {logs_dir}")

    # Generate log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(logs_dir, f"telegram_summarizer_{timestamp}.log")

    # Remove default logger
    logger.remove()

    # Always log to file at DEBUG level, regardless of debug mode
    logger.add(log_file, level="DEBUG", rotation="10 MB", retention="1 week")

    # Log initialization message
    logger.debug(f"Logging initialized.")

    return log_file

async def main():
    """Main entry point for the script"""
    try:
        
        # Configure logger based on debug mode
        log_file = setup_logging()
        
        # Check for .env file and load environment variables
        env_vars = check_env_file()

        # Parse command line arguments
        args = parse_args()

        
        if args.job:
            # Load the templates file
            chat_templates, prompt_templates, job_templates = read_templates_file()
            job_template = job_templates.get(args.job)
            if job_template:
                logger.info(f"Executing with Job template '{args.job}' found in Templates.txt")
                # Parse the job template
                job_args = job_template.split()
                # Override the command line arguments with the job template
                args = parse_args(job_args)
                
            else:
                console.print(f"[bold red]Error: Job template '{args.job}' not found in Templates.txt[/bold red]")
                sys.exit(1)

    
        logger.debug("Starting Telegram Summarizer")
        logger.debug(f"Mode: {'Debug' if args.debug else 'Normal'}")
        logger.debug(f"Arguments: {args}")
        logger.debug(f"Environment variables loaded: {', '.join(env_vars.keys())}")
        logger.debug(f"Log file: {log_file}")

        # Run the Telegram client with the parsed arguments
        await run_telegram_client(args, env_vars)
    except Exception as e:
        error_text = Text("An error occurred!", style="bold red")
        help_text = Text(f"\nError details: {e}", style="yellow")

        console.print(Panel(
            error_text + help_text,
            title="Runtime Error",
            border_style="red",
            expand=False
        ))

        # Log the error
        logger.error(f"Runtime error: {str(e)}")
        logger.exception("Exception details:")

        sys.exit(1)

if __name__ == "__main__":
    
    
    # Run the async main function
    asyncio.run(main())
