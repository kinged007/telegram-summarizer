import sys
import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from loguru import logger

# Import modules from src directory
from src.config import check_env_file, parse_args
from src.templates import read_templates_file
from src.logging_utils import setup_logging
from src.telegram_utils import run_telegram_client
from src.job_utils import process_job_templates

# Initialize Rich console for the main block
console = Console()


async def main():
    """Main entry point for the script"""
    try:
        # Check for .env file and load environment variables
        env_vars = check_env_file()

        # Parse command line arguments
        args = parse_args()

        # Configure logger based on debug mode
        log_file = setup_logging(args.debug)

        logger.debug("Starting Telegram Summarizer")
        logger.debug(f"Mode: {'Debug' if args.debug else 'Normal'}")

        # Process job templates if specified
        if args.job:
            # Load the templates file (only need job_templates here)
            _, _, job_templates = read_templates_file()

            # Process job templates
            jobs_processed = await process_job_templates(args, env_vars, job_templates)

            # If jobs were processed, exit
            if jobs_processed:
                return

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
