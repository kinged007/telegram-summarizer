"""
Console utilities module for Telegram Summarizer.
Contains functions for displaying information in the console using Rich.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TimeElapsedColumn, TaskProgressColumn

# Initialize Rich console
console = Console()

def create_progress_bar():
    """
    Create a Rich progress bar with standard configuration.
    
    Returns:
        Progress: A configured Rich progress bar
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("•"),
        TimeElapsedColumn()
    )

def display_error(title, error_message, help_text=None):
    """
    Display an error message in a Rich panel.
    
    Args:
        title (str): The title of the error panel
        error_message (str): The main error message
        help_text (str, optional): Additional help text
    """
    error_text = Text(error_message, style="bold red")
    
    if help_text:
        help_rich_text = Text(f"\n{help_text}", style="yellow")
        content = error_text + help_rich_text
    else:
        content = error_text
        
    console.print(Panel(
        content,
        title=title,
        border_style="red",
        expand=False
    ))

def display_success(message, title="Success"):
    """
    Display a success message in a Rich panel.
    
    Args:
        message (str): The success message
        title (str, optional): The title of the success panel
    """
    console.print(Panel(
        Text(message, style="bold green"),
        title=title,
        border_style="green"
    ))

def display_debug_info(provider, model, prompt_tokens, completion_tokens, total_tokens, 
                      formatted_cost, response_time, is_mock=False):
    """
    Display debug information in a Rich panel.
    
    Args:
        provider (str): The LLM provider
        model (str): The LLM model
        prompt_tokens (int): Number of prompt tokens
        completion_tokens (int): Number of completion tokens
        total_tokens (int): Total number of tokens
        formatted_cost (str): Formatted cost string
        response_time (float): Response time in seconds
        is_mock (bool, optional): Whether this is a mock response
    """
    mock_indicator_bold = "[bold red](MOCK RESPONSE)[/bold red] " if is_mock else ""
    cost_indicator = " (simulated)" if is_mock else ""
    
    debug_panel = Panel(
        Text.from_markup(
            f"[bold]Debug Information:[/bold]\n\n"
            f"[yellow]Provider:[/yellow] {provider} {mock_indicator_bold}\n"
            f"[yellow]Model:[/yellow] {model}\n"
            f"[yellow]Prompt Tokens:[/yellow] {prompt_tokens}\n"
            f"[yellow]Completion Tokens:[/yellow] {completion_tokens}\n"
            f"[yellow]Total Tokens:[/yellow] {total_tokens}\n"
            f"[yellow]Cost:[/yellow] ${formatted_cost}{cost_indicator}\n"
            f"[yellow]Response Time:[/yellow] {response_time:.2f}s\n"
            f"[yellow]Log Directory:[/yellow] ./logs/\n"
        ),
        title=f"{'Mock ' if is_mock else ''}LLM Response Details",
        border_style="yellow"
    )
    console.print(debug_panel)
