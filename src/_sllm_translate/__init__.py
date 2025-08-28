import sys
import subprocess
import tempfile
import textwrap
import os
import importlib.resources
import argparse
import traceback
import logging

import sllm.api
import sllm.common
import sllm.container

logger = logging.getLogger(__name__)


def read_from_editor() -> str:
    editor: str = os.getenv("EDITOR", "")
    if editor == "":
        raise RuntimeError("No $EDITOR is set.")

    with tempfile.NamedTemporaryFile("r+") as handle:
        subprocess.call([editor, handle.name])
        handle.seek(0)
        return handle.read()


def communicate_request(message: str) -> None:
    """Formats the commit message and prints it."""
    if not sys.stdout.isatty():
        logger.debug("Not in interactive console, omitting input.")
        return

    for long_line in message.split("\n"):
        for line in textwrap.wrap(
            long_line, width=os.get_terminal_size().columns - 3
        ):
            print("| \033[3m" if sllm.common.use_color() else "| ", end="")
            print(line, end="")
            print("\033[0m" if sllm.common.use_color() else "", end="\n")


def app() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Translate text into English. "
            "Leaving the input empty will open $EDITOR window."
        )
    )
    parser.add_argument("--debug", action="store_true", help="nerd information")
    parser.add_argument("input", nargs="*", help="read from argv")

    args = parser.parse_args()

    message: str = ""
    if len(args.input):
        message = " ".join(args.argv)
    else:
        message = read_from_editor()

    sllm.container.ensure_runtime()
    sllm.container.ensure_started()
    sllm.container.schedule_shutdown()

    communicate_request(message)

    logger.info("Translating...")
    request = sllm.api.Request(
        prompt=(
            importlib.resources.files("_sllm_translate")
            .joinpath("prompt.txt")
            .read_text()
        ),
        query=message,
        example_input_header="[Original]",
        example_response_header="[Translation]",
    )
    translation: str = request.send()
    print(translation)


def main() -> int:
    debug: bool = "--debug" in sys.argv
    sllm.common.configure_logging(debug=debug)

    try:
        app()
        return 0
    except KeyboardInterrupt:
        logger.error("Interrupted.")
        return 0
    except Exception as exc:
        logger.critical("Aborting on unhandled exception.")
        if debug:
            traceback.print_exc()
        else:
            print(exc.__class__.__name__, exc)
        return 1
