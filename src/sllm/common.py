import logging
import sys

API_PORT: int = 6574
API_URL: str = f"http://127.0.0.1:{API_PORT}"


def configure_logging(debug: bool = False) -> None:
    urllib_logger = logging.getLogger("urllib3")
    urllib_logger.setLevel(logging.ERROR)

    root_logger = logging.getLogger()

    if debug:
        root_logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(stream=sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                fmt=(
                    "{asctime} "
                    "\033[33m{levelname:<5}\033[0m "
                    "\033[32m{name}:{funcName}:{line}\033[0m "
                    "\033[2m{message}\033[0m"
                ),
                style="{",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root_logger.addHandler(handler)
    else:
        root_logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(stream=sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                fmt=("\033[33m{levelname}\033[0m \033[2m{message}\033[0m"),
                style="{",
            )
        )
        root_logger.addHandler(handler)
