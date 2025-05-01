"""
Telegram utilities module for Telegram Summarizer.
Contains functions for interacting with the Telegram API.
"""

from datetime import datetime, timedelta
from telethon import TelegramClient
from loguru import logger
from rich.panel import Panel
from rich.text import Text

from .console_utils import console
from .templates import resolve_chat_id
from .message_utils import fetch_messages_from_chat

async def run_telegram_client(args, env_vars):
    """
    Initialize and run the Telegram client with the parsed arguments.

    Args:
        args: The parsed command line arguments
        env_vars (dict): Dictionary of environment variables
    """
    # Extract environment variables for Telegram client
    api_id = env_vars['api_id']
    api_hash = env_vars['api_hash']
    # Note: LLM variables will be used in process_telegram_data

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

async def process_chat_id_argument(arg, templates, client, entity_type="chat"):
    """
    Process a chat ID argument, handling comma-separated values and resolving names to IDs.

    Args:
        arg (str): The argument to process
        templates (dict): Dictionary of chat templates for name resolution
        client (TelegramClient): The Telegram client instance
        entity_type (str, optional): Type of entity for error messages (e.g., "chat", "send target")

    Returns:
        list: List of resolved chat IDs (strings or integers)
    """
    result_ids = []

    # Check if this argument contains commas
    if ',' in arg:
        # Split by comma and process each part
        for item in arg.split(','):
            await process_single_chat_id(item.strip(), templates, client, entity_type, result_ids)
    else:
        # Process as a single item
        await process_single_chat_id(arg.strip(), templates, client, entity_type, result_ids)

    return result_ids

async def process_single_chat_id(chat_id, templates, client, entity_type, result_ids):
    """
    Process a single chat ID, resolving it and adding to the result list.

    Args:
        chat_id (str): The chat ID or name to process
        templates (dict): Dictionary of chat templates for name resolution
        client (TelegramClient): The Telegram client instance
        entity_type (str): Type of entity for error messages
        result_ids (list): List to append resolved IDs to
    """
    from .console_utils import console

    if not chat_id:
        return

    # Resolve chat name to ID if needed
    resolved_chat = resolve_chat_id(chat_id, templates)
    if not resolved_chat:
        console.print(f"[bold red]Error: {entity_type.capitalize()} '{chat_id}' not found in Templates.txt[/bold red]")
        return

    # Handle chat IDs with underscores (e.g., -100123456_789)
    if '_' in resolved_chat:
        result_ids.append(resolved_chat)
        logger.debug(f"Added {entity_type} with underscore: {resolved_chat}")
    else:
        try:
            # Try to convert to integer
            _id = int(resolved_chat)
            result_ids.append(_id)
            logger.debug(f"Added numeric {entity_type}: {resolved_chat}")
        except ValueError:
            console.print(f"[bold red]Error: Invalid chat ID format for {entity_type} '{chat_id}' (resolved to '{resolved_chat}')[/bold red]")
            try:
                console.print(f"[bold red]Fetching entity for {entity_type} '{chat_id}' (resolved to '{resolved_chat}')...[/bold red]")
                entity = await client.get_entity(resolved_chat)
                result_ids.append(entity.id)
                logger.debug(f"Added {entity_type}: {resolved_chat}")
            except Exception as e2:
                console.print(f"[bold red]Error: Invalid chat ID for {entity_type} '{chat_id}' (resolved to '{resolved_chat}'): {str(e2)}[/bold red]")

async def fetch_messages(client, chat_id, days, progress=None, task_id=None):
    """
    Fetch messages from a Telegram chat.

    Args:
        client (TelegramClient): The Telegram client instance
        chat_id (str or int): The chat ID to fetch messages from
        days (int): Number of days to look back
        progress (Progress, optional): Progress bar instance
        task_id (int, optional): Task ID for the progress bar

    Returns:
        list: List of fetched messages
    """
    # Calculate the date from which to fetch messages
    offset_date = datetime.now() - timedelta(days=days)
    # Set to midnight of that day
    offset_date = offset_date.replace(hour=0, minute=0, second=0, microsecond=0)

    logger.debug(f"Fetching messages from chat ID {chat_id} since {offset_date}")

    # Handle chat IDs with underscores for topics
    message_thread_id = None
    entity_chat_id = chat_id

    if isinstance(chat_id, str) and '_' in chat_id:
        base_chat_id, thread_id = chat_id.split('_')
        message_thread_id = int(thread_id)
        entity_chat_id = int(base_chat_id)
        logger.debug(f"Fetching from topic: base chat ID {base_chat_id}, thread ID {thread_id}")

    # Get channel information
    try:
        channel_entity = await client.get_entity(entity_chat_id)
        if hasattr(channel_entity, 'title'):
            channel_name = channel_entity.title
        elif hasattr(channel_entity, 'first_name'):
            channel_name = f"{channel_entity.first_name} {getattr(channel_entity, 'last_name', '')}"
        else:
            channel_name = "Unknown"

        logger.debug(f"Channel info: {channel_name} (ID: {chat_id})")
    except Exception as e:
        logger.error(f"Error getting channel info: {str(e)}")
        channel_name = "Unknown"

    # Fetch messages
    messages = []
    try:
        async for message in client.iter_messages(
            entity_chat_id,
            offset_date=offset_date,
            reverse=True,
            limit=None
        ):
            # Skip messages not in the specified thread if thread_id is provided
            if message_thread_id is not None and getattr(message, 'reply_to', None) is not None:
                reply_to = message.reply_to
                if not (hasattr(reply_to, 'reply_to_msg_id') and reply_to.reply_to_msg_id == message_thread_id):
                    if not (hasattr(reply_to, 'forum_topic') and reply_to.forum_topic and
                            hasattr(reply_to, 'top_msg_id') and reply_to.top_msg_id == message_thread_id):
                        continue

            # Skip empty or service messages
            if not message.text:
                continue

            # Format the message
            sender = "Unknown"
            if message.sender:
                if hasattr(message.sender, 'first_name'):
                    sender = f"{message.sender.first_name} {getattr(message.sender, 'last_name', '')}"
                elif hasattr(message.sender, 'title'):
                    sender = message.sender.title

            # Format date as ISO format
            date_str = message.date.strftime('%Y-%m-%d %H:%M:%S')

            # Add to messages list
            messages.append({
                'date': date_str,
                'sender': sender,
                'text': message.text
            })

            # Update progress if provided
            if progress and task_id is not None:
                progress.update(task_id, advance=0.5)  # Increment by a small amount for each message

    except Exception as e:
        logger.error(f"Error fetching messages from {chat_id}: {str(e)}")

    # Update progress to completion if provided
    if progress and task_id is not None:
        progress.update(task_id, completed=True)

    logger.info(f"Fetched {len(messages)} messages from {channel_name} (ID: {chat_id})")
    return messages

async def send_message_to_chat(client, send_id, message_content):
    """
    Send a message to a Telegram chat.

    Args:
        client (TelegramClient): The Telegram client instance
        send_id (str or int): The chat ID to send the message to
        message_content (str): The message content to send

    Returns:
        bool: True if successful, False otherwise
    """
    from .console_utils import console

    logger.info(f"Sending message to Telegram chat ID: {send_id}")

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
        await client.send_message(entity, message_content, reply_to=message_thread_id)
        console.print(f"[bold green]Message sent to Telegram chat ID: [/bold green][yellow]{send_id}[/yellow]")
        logger.info(f"Message successfully sent to Telegram chat ID: {send_id}")
        return True
    except Exception as e:
        error_msg = f"Error sending message to {send_id}: {str(e)}"
        logger.error(error_msg)
        console.print(f"[bold red]{error_msg}[/bold red]")
        return False

async def process_telegram_data(client, args, env_vars):
    """
    Process Telegram data and generate summary.
    This is the main function that orchestrates the entire process.

    Args:
        client (TelegramClient): The Telegram client instance
        args: The parsed command line arguments
        env_vars (dict): Dictionary of environment variables
    """
    import os
    from .console_utils import console, create_progress_bar, display_success, display_debug_info
    from .templates import read_templates_file, resolve_prompt_template, process_prompt_template_argument
    from .llm_utils import format_messages_for_prompt, call_llm

    # Extract environment variables
    llm_provider = env_vars['llm_provider']
    llm_model = env_vars['llm_model']
    llm_api_key = env_vars['llm_api_key']

    # Prepare the base prompt
    console.print("[bold blue]Setting up...[/bold blue]")

    # Load the templates file (only need chat and prompt templates here)
    chat_templates, prompt_templates, _ = read_templates_file()

    # Process chat IDs - handle both comma-separated values and multiple arguments
    chat_ids = []
    for chat_arg in args.chats:
        chat_ids.extend(await process_chat_id_argument(chat_arg, chat_templates, client, "chat"))

    if not chat_ids:
        console.print("[bold red]Error: No valid chat IDs provided[/bold red]")
        return

    # Get system prompt from environment or template
    system_prompt = os.getenv('PROMPT_SYSTEM', 'You are an expert AI assistant specialized in summarizing Telegram conversations.')

    # Check if there's a template override for system prompt
    system_template = resolve_prompt_template('PROMPT_SYSTEM', prompt_templates)
    if system_template:
        system_prompt = system_template
        logger.debug("Using system prompt from Templates.txt")

    # Get user prompt from environment or template
    user_prompt = os.getenv('PROMPT_TEXT', 'Please analyze these Telegram conversations and provide a comprehensive summary.')

    # Check if there's a template override for user prompt
    user_template = resolve_prompt_template('PROMPT_TEXT', prompt_templates)
    if user_template:
        user_prompt = user_template
        logger.debug("Using user prompt from Templates.txt")

    # Process prompt templates if specified
    prompt_template_texts = []
    if args.prompt_template:
        for template_arg in args.prompt_template:
            template_texts = await process_prompt_template_argument(template_arg, prompt_templates)
            prompt_template_texts.extend(template_texts)

    # Combine all prompt templates
    combined_prompt_template = "\n\n".join(prompt_template_texts) if prompt_template_texts else ""

    # Create a single progress display for the entire process
    with create_progress_bar() as progress:
        # Add tasks for each stage
        overall_task = progress.add_task("[bold green]Overall Progress", total=100, completed=5)
        fetch_task = progress.add_task("[bold blue]Fetching messages", total=len(chat_ids), visible=False)

        # Update overall progress - 10%
        progress.update(overall_task, completed=10)

        # Make fetch task visible when we start fetching
        progress.update(fetch_task, visible=True)

        # Fetch messages from each chat
        all_messages = []
        for i, chat_id in enumerate(chat_ids):
            # Update task description to show current chat ID
            progress.update(fetch_task, description=f"[bold blue]Fetching from chat {chat_id} ({i+1}/{len(chat_ids)})")

            # Fetch messages
            messages, channel_name, _ = await fetch_messages_from_chat(client, chat_id, args.days, progress, fetch_task)
            all_messages.extend(messages)

            # Log the message count
            logger.info(f"Added {len(messages)} messages from {channel_name} (ID: {chat_id}) to the prompt")

            # Update progress
            progress.update(fetch_task, advance=1)

        # Update overall progress - 50%
        progress.update(overall_task, completed=50, description="[bold blue]Preparing messages for AI...")

        # Sort all messages by date
        all_messages.sort(key=lambda x: x['date'])

        # Format messages for the prompt
        full_prompt = format_messages_for_prompt(
            all_messages,
            system_prompt,
            user_prompt,
            args.prompt if args.prompt else combined_prompt_template
        )

        # Update overall progress - 60%
        progress.update(overall_task, completed=60, description=f"[bold blue]Initializing LiteLLM with {llm_provider}/{llm_model}...")

        # Update overall progress - 70%
        progress.update(overall_task, completed=70, description="[bold blue]Generating summary with AI...")

        # Add AI processing task
        ai_task = progress.add_task("[yellow]AI Processing", total=None)

        # Call the LLM
        try:
            response, time_taken, prompt_tokens, completion_tokens, total_tokens, raw_cost = call_llm(
                full_prompt, llm_provider, llm_model, llm_api_key, args.mock
            )

            # Format the cost with 5 decimal places
            formatted_cost = f"{float(raw_cost):.10f}" if isinstance(raw_cost, (int, float)) else 'N/A'

            # Update overall progress - 80%
            progress.update(overall_task, completed=80, description="[bold blue]Summary generated!")

            # Remove AI task
            progress.remove_task(ai_task)

            # Check if we need to send to Telegram
            send_ids = []
            for send_arg in args.send:
                send_ids.extend(await process_chat_id_argument(send_arg, chat_templates, client, "send target"))

            if send_ids:
                # Update overall progress - 85%
                progress.update(overall_task, completed=85, description="[bold blue]Sending to Telegram...")

                # Add sending task
                send_task = progress.add_task("[cyan]Sending to Telegram", total=len(send_ids))

                # Send response to the specified channel(s)
                for i, send_id in enumerate(send_ids):
                    logger.info(f"Sending summary to Telegram chat ID: {send_id}")

                    # Update task description to show current chat ID
                    progress.update(send_task, description=f"[cyan]Sending to chat {send_id} ({i+1}/{len(send_ids)})")

                    # Send the message
                    await send_message_to_chat(client, send_id, response.choices[0].message.content)

                    # Update progress
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

        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            console.print(f"[bold red]Error generating summary: {str(e)}[/bold red]")
            return

    # Final confirmation message
    if send_ids:
        success_message = "Summary successfully generated and sent to Telegram!"
    else:
        success_message = "Summary successfully generated!"

    display_success(success_message, "Process Complete")

    # Display the summary in the console
    console.print(Panel(
        Text(response.choices[0].message.content, style="white"),
        title="Generated Summary",
        border_style="blue"
    ))

    # Add mock mode indicator if applicable
    mock_indicator = " [dim](simulated)[/dim]" if args.mock else ""

    # Always display cost and token information
    console.print(f"[bold blue]Completion Cost: [/bold blue][green]${formatted_cost}{mock_indicator}[/green]")
    console.print(f"[bold blue]Tokens: [/bold blue][green]Prompt: {prompt_tokens} | Completion: {completion_tokens} | Total: {total_tokens}{mock_indicator}[/green]")
    console.print(f"[bold blue]Response Time: [/bold blue][green]{time_taken:.2f}s[/green]")

    # Display additional debug information if debug mode is enabled
    if args.debug:
        display_debug_info(
            llm_provider, llm_model,
            prompt_tokens, completion_tokens, total_tokens,
            formatted_cost, time_taken, args.mock
        )

    # Process job templates if specified
    if args.job:
        # This would be handled in the main function, not here
        pass
