import time
from collections.abc import Generator
from contextlib import contextmanager


@contextmanager
def time_block() -> Generator[dict[str, float], None, None]:
    """Context manager to measure execution time of a code block in seconds.

    Yields:
        A dictionary containing a single key "duration" which is updated
        with the final elapsed time upon exiting the context.
    """
    elapsed = {"duration": 0.0}
    start_time = time.perf_counter()
    try:
        yield elapsed
    finally:
        elapsed["duration"] = time.perf_counter() - start_time
