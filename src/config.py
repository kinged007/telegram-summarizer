"""
Configuration module for Telegram Summarizer.
Contains functions for parsing command line arguments and checking environment variables.
"""

import argparse
import os
import sys
import shlex
import re
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from loguru import logger

# Initialize Rich console
console = Console()

def check_env_file():
    """
    Check if .env file exists and load environment variables.
    Returns a dictionary with the required environment variables.
    """
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

def parse_args(args=None):
    """
    Parse command line arguments.
    Returns the parsed arguments.
    """
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
                      help='Name of job template(s) from Templates.txt to execute (can be comma-separated or multiple values)',
                      nargs='*',
                      type=str,
                      default=[])

    args, _ = parser.parse_known_args(args)  # Ignore unknown arguments

    # if no arguments are passed, then we stop the script here.
    if not any(vars(args).values()):
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

    return args
