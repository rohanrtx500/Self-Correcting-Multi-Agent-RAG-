from loguru import logger
from rich.logging import RichHandler


def setup_logger(log_level: str = "INFO") -> None:
    """Configures Loguru logger to output formatted logs via RichHandler.

    Args:
        log_level: The threshold logging level (e.g. INFO, DEBUG).
    """
    # Remove default handler
    logger.remove()

    # Add custom Rich-based handler for stdout
    logger.add(
        RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_time=True,
            show_level=True,
            show_path=False,
        ),
        format="[bold cyan]•[/] {message}",
        level=log_level,
        backtrace=True,
        diagnose=True,
    )


# Helper function to print visually formatted node starts/ends
def log_node_start(node_name: str) -> None:
    """Logs the start of a graph node execution with distinct styling.

    Args:
        node_name: Name of the node entering execution.
    """
    logger.info(f"[bold yellow]> Node Start:[/] [bold white]{node_name}[/]")


def log_node_end(node_name: str, duration: float) -> None:
    """Logs the completion of a graph node with its duration.

    Args:
        node_name: Name of the completed node.
        duration: Duration of execution in seconds.
    """
    logger.info(
        f"[bold green][OK] Node Finish:[/] [bold white]{node_name}[/] [dim]({duration:.3f}s)[/]"
    )
