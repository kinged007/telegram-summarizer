"""
Message utilities module for Telegram Summarizer.
Contains functions for fetching and processing messages from Telegram.
"""

from datetime import datetime, timedelta
from loguru import logger
from rich.progress import Progress

from .console_utils import console

async def fetch_messages_from_chat(client, chat_id, days, progress=None, task_id=None):
    """
    Fetch messages from a Telegram chat with detailed progress tracking.
    
    Args:
        client (TelegramClient): The Telegram client instance
        chat_id (str or int): The chat ID to fetch messages from
        days (int): Number of days to look back
        progress (Progress, optional): Progress bar instance
        task_id (int, optional): Task ID for the progress bar
        
    Returns:
        tuple: (messages, channel_name, total_messages)
    """
    # Calculate midnight of args.days ago
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    offset_date = today - timedelta(days=days)
    
    # Always log time range to file
    logger.debug(f"Fetching messages from chat {chat_id} from {offset_date} to now")
    logger.debug(f"Time range: {offset_date.strftime('%Y-%m-%d %H:%M')} to {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
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
        channel_name = "Unknown"
    
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
        logger.warning(msg)
        if progress and task_id is not None:
            progress.update(task_id, advance=1)
        return [], channel_name, 0
    
    logger.info(f"Fetching {total_messages} messages from channel ID: {chat_id}")
    
    # Add a task for message fetching with channel name if available
    channel_name_display = f"{channel_name}" if channel_name != "Unknown" else f"{chat_id}"
    message_task = None
    if progress:
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
        # Skip empty or service messages
        if not message.text:
            continue
        
        # Get sender information
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
        
        # Store the last 3 messages for debug output
        if len(last_messages) >= 3:
            last_messages.pop(0)
        last_messages.append(f"{date_str}:{sender}:{message.text[:50]}...")
        
        # Update progress
        count += 1
        if progress and message_task:
            progress.update(message_task, completed=count)
    
    # Ensure the progress bar reaches 100%
    if progress and message_task and count < total_messages:
        progress.update(message_task, completed=total_messages)
    
    # Log the last 3 messages for debugging
    if last_messages:
        logger.debug(f"Last messages from {chat_id}:")
        for msg in last_messages:
            logger.debug(f"  {msg}")
    
    # Remove the message task when done
    if progress and message_task:
        progress.remove_task(message_task)
    
    # Update fetch progress if provided
    if progress and task_id is not None:
        progress.update(task_id, advance=1)
    
    logger.info(f"Fetched {len(messages)} messages from {channel_name} (ID: {chat_id})")
    return messages, channel_name, total_messages
