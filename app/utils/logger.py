import contextvars
from typing import Any

from loguru import logger
from rich.logging import RichHandler

# Context variable for request correlation ID
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="system")


def get_request_id() -> str:
    """Retrieves current request ID from context."""
    return request_id_ctx.get()


def set_request_id(req_id: str) -> None:
    """Sets current request ID in context."""
    request_id_ctx.set(req_id)


def setup_logger(log_level: str = "INFO") -> None:
    """Configures Loguru logger with structured formatting and request ID patcher.

    Args:
        log_level: The threshold logging level (e.g. INFO, DEBUG).
    """
    # Remove default handler
    logger.remove()

    def request_id_patcher(record: Any) -> None:
        record["extra"]["request_id"] = request_id_ctx.get()

    logger.configure(patcher=request_id_patcher)

    def log_format(record: Any) -> str:
        req_id = record["extra"].get("request_id") or request_id_ctx.get()
        return f"[dim]{req_id}[/] [bold cyan]•[/] {{message}}\n"

    # Add custom Rich-based handler for stdout
    logger.add(
        RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_time=True,
            show_level=True,
            show_path=False,
        ),
        format=log_format,
        level=log_level,
        backtrace=True,
        diagnose=False,  # Set diagnose=False in production to avoid leaking variables in tracebacks
    )


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
