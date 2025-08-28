import logging
import os
import sys

API_PORT: int = 6574
API_URL: str = f"http://127.0.0.1:{API_PORT}"
MODEL: str = os.getenv("SLLM_MODEL", "llama3.2:3b")


def use_color() -> bool:
    """Determine if stdout/stderr support colors."""
    if not sys.stdout.isatty():
        return False
    if os.getenv("NO_COLOR", None) is not None:
        return False
    return True


def configure_logging(debug: bool = False) -> None:
    urllib_logger = logging.getLogger("urllib3")
    urllib_logger.setLevel(logging.ERROR)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    handler = logging.StreamHandler(stream=sys.stderr)

    if debug:
        if use_color():
            fmt = (
                "{asctime} "
                "\033[33m{levelname:<5}\033[0m "
                "\033[32m{name}:{funcName}:{lineno}\033[0m "
                "\033[2m{message}\033[0m"
            )
        else:
            fmt = (
                "{asctime} {levelname:<5} {name}:{funcName}:{lineno} {message}"
            )
    else:
        if use_color():
            fmt = "\033[33m{levelname}\033[0m \033[2m{message}\033[0m"
        else:
            fmt = "{levelname} {message}"

    handler.setFormatter(
        logging.Formatter(fmt=fmt, style="{", datefmt="%Y-%m-%d %H:%M:%S")
    )
    root_logger.addHandler(handler)
