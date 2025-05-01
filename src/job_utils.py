"""
Job utilities module for Telegram Summarizer.
Contains functions for processing job templates.
"""

import sys
import shlex
from loguru import logger
from rich.console import Console

from .config import parse_args
from .logging_utils import setup_logging
from .telegram_utils import run_telegram_client

# Initialize Rich console
console = Console()

async def process_job_templates(args, env_vars, job_templates):
    """
    Process job templates from Templates.txt.
    
    Args:
        args: The parsed command line arguments
        env_vars (dict): Dictionary of environment variables
        job_templates (dict): Dictionary of job templates
        
    Returns:
        bool: True if jobs were processed, False if no valid jobs were found
    """
    # Process job templates - handle both comma-separated values and multiple arguments
    job_names = []
    for job_arg in args.job:
        # Handle comma-separated values
        if ',' in job_arg:
            # Split by comma and process each part
            for item in job_arg.split(','):
                if item.strip():
                    job_names.append(item.strip())
        else:
            # Process as a single item
            if job_arg.strip():
                job_names.append(job_arg.strip())

    # Store CLI flags before they get overridden by job templates
    cli_debug_mode = args.debug
    cli_mock_mode = args.mock

    # Process each job template
    if job_names:
        for job_name in job_names:
            job_template = job_templates.get(job_name)
            if job_template:
                console.print(f"[bold blue]Executing job template: [/bold blue][yellow]{job_name}[/yellow]")
                logger.info(f"Executing with Job template '{job_name}' found in Templates.txt")
                # Parse the job template while respecting quoted strings
                job_args = shlex.split(job_template)

                # Override the command line arguments with the job template
                job_args_parsed = parse_args(job_args)

                # Preserve CLI flags - they take precedence over job template settings
                if cli_debug_mode:
                    job_args_parsed.debug = True
                    console.print("[bold blue]Using debug mode from command line[/bold blue]")

                if cli_mock_mode:
                    job_args_parsed.mock = True
                    console.print("[bold blue]Using mock mode from command line[/bold blue]")

                # Configure logger based on debug mode (from CLI or job template)
                log_file = setup_logging(job_args_parsed.debug)

                logger.debug(f"Starting Telegram Summarizer for job: {job_name}")
                logger.debug(f"Mode: {'Debug' if job_args_parsed.debug else 'Normal'}")
                logger.debug(f"Arguments: {job_args_parsed}")
                logger.debug(f"Environment variables loaded: {', '.join(env_vars.keys())}")
                logger.debug(f"Log file: {log_file}")

                # Run the Telegram client with the parsed arguments for this job
                await run_telegram_client(job_args_parsed, env_vars)

                console.print(f"[bold green]Completed job: {job_name}[/bold green]")
            else:
                console.print(f"[bold red]Error: Job template '{job_name}' not found in Templates.txt[/bold red]")

        # All jobs have been processed
        return True
    else:
        console.print("[bold red]Error: No valid job templates specified[/bold red]")
        sys.exit(1)
        
    return False
