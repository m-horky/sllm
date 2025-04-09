import sys
import subprocess
import tempfile
import textwrap
import os
import importlib.resources
import argparse
import pathlib
import traceback
import logging

import sllm.api
import sllm.common
import sllm.container

logger = logging.getLogger(__name__)


def is_input_piped() -> bool:
    return not os.isatty(sys.stdin.fileno())


def read_from_pipe() -> str:
    return sys.stdin.read()


def read_from_file(file: pathlib.Path) -> str:
    with file.open("r") as handle:
        return handle.read()


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
    parser = argparse.ArgumentParser()
    flags = parser.add_mutually_exclusive_group()
    flags.add_argument(
        "--pipe", action="store_true", help="read from pipe (default)"
    )
    flags.add_argument("--edit", action="store_true", help="open editor")
    flags.add_argument("--file", type=pathlib.Path, help="read from file")
    parser.add_argument("--debug", action="store_true", help="nerd information")

    args = parser.parse_args()

    message: str = ""
    if args.pipe or is_input_piped():
        message = read_from_pipe()
    elif args.edit:
        message = read_from_editor()
    elif args.file:
        message = read_from_file(args.file)
    else:
        parser.print_help()
        return

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
    response: dict = request.send()

    translation: str = response["choices"][0]["message"]["content"].strip()
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
