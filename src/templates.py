"""
Templates module for Telegram Summarizer.
Contains functions for reading and resolving templates from Templates.txt.
"""

import os
import re
from loguru import logger
from rich.console import Console

# Initialize Rich console
console = Console()

def read_templates_file():
    """
    Read the Templates.txt file and return dictionaries for chat IDs, prompt templates, and job templates.

    Returns:
        tuple: (chat_templates, prompt_templates, job_templates)
    """
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
    """
    Resolve a chat ID or name to a numeric chat ID.

    Args:
        chat_arg (str): The chat ID or name to resolve
        chat_templates (dict): Dictionary of chat templates for name resolution

    Returns:
        str or None: The resolved chat ID or None if not found
    """
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
    """
    Resolve a prompt template name to the actual template text.

    Args:
        template_name (str): The template name to resolve
        prompt_templates (dict): Dictionary of prompt templates for name resolution

    Returns:
        str or None: The resolved template text or None if not found
    """
    if template_name in prompt_templates:
        logger.debug(f"Using prompt template '{template_name}'")
        return prompt_templates[template_name]

    # If not found, return None
    logger.error(f"Prompt template '{template_name}' not found in Templates.txt")
    return None


async def process_prompt_template_argument(arg, templates):
    """
    Process a prompt template argument, handling comma-separated values.

    Args:
        arg (str): The argument to process
        templates (dict): Dictionary of prompt templates for name resolution

    Returns:
        list: List of resolved template texts
    """
    result_texts = []

    # Check if this argument contains commas
    if ',' in arg:
        # Split by comma and process each part
        for item in arg.split(','):
            await process_single_prompt_template(item.strip(), templates, result_texts)
    else:
        # Process as a single item
        await process_single_prompt_template(arg.strip(), templates, result_texts)

    return result_texts


async def process_single_prompt_template(template_name, templates, result_texts):
    """
    Process a single prompt template, resolving it and adding to the result list.

    Args:
        template_name (str): The template name to process
        templates (dict): Dictionary of prompt templates for name resolution
        result_texts (list): List to append resolved template texts to
    """
    if not template_name:
        return

    # Resolve template name to text
    resolved_template = resolve_prompt_template(template_name, templates)
    if resolved_template:
        result_texts.append(resolved_template)
    else:
        console.print(f"[bold yellow]Warning: Prompt template '{template_name}' not found in Templates.txt, skipping[/bold yellow]")
