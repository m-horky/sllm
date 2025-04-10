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
        if not len(long_line):
            print("|")
            continue
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
        "--from-signature",
        action="store_true",
        help="implement function for a given signature",
    )
    parser.add_argument("--debug", action="store_true", help="nerd information")

    args = parser.parse_args()
    prompt: str | None = None
    if args.from_signature:
        prompt = "implement.prompt"
    else:
        parser.print_help()
        return

    message: str = read_from_editor()

    sllm.container.ensure_runtime()
    sllm.container.ensure_started()
    sllm.container.schedule_shutdown()

    communicate_request(message)

    logger.info("Coding...")
    request = sllm.api.Request(
        prompt=(
            importlib.resources.files("_sllm_code").joinpath(prompt).read_text()
        ),
        query=message,
        example_input_header="",
        example_response_header="",
    )
    response: dict = request.send()

    snippet: str = response["choices"][0]["message"]["content"].strip()
    print(snippet)


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
