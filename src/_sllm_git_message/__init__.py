import sys
import importlib.resources
import subprocess
import argparse
import pathlib
import traceback
import logging

import sllm.api
import sllm.common
import sllm.container

logger = logging.getLogger(__name__)


def read_from_file(file: pathlib.Path) -> str:
    """Read git message from a file.

    This is mostly used by the hook to read ~/.git/COMMIT_MSG.
    """
    with file.open("r") as handle:
        raw = handle.readlines()

    # Clean up the comments
    message: str = ""
    for line in raw:
        if line.startswith("#"):
            continue
        message += line.rstrip() + "\n"

    # Clean up trailing newlines
    return message.strip()


def read_from_ref(reference: str) -> str:
    """Read git message from existing reference."""
    cmd = ["git", "show", "--format=%B", "--no-patch", reference]

    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode > 0:
        logger.error(
            f"Got {proc.returncode} from 'git show': {proc.stderr.strip()}"
        )
        raise RuntimeError("Could not read reference.")

    # Clean up trailing lines
    return proc.stdout.strip()


def communicate_request(message: str) -> None:
    """Formats the commit message and prints it."""
    # TODO Wrap long lines
    for line in message.split("\n"):
        print("| \033[3m" if sllm.common.use_color() else "| ", end="")
        print(line, end="")
        print("\033[0m" if sllm.common.use_color() else "", end="\n")


def communicate_response(review: str) -> bool:
    """Communitcates the LLM response to the user.

    :returns: True if the code is considered good.
    """

    def is_ok(text: str) -> bool:
        return "meh" not in text.lower()

    for line in review.split("\n"):
        if sllm.common.use_color():
            print("\033[32m" if is_ok(line) else "\033[31m", end="")
        print(line, end="")
        print("\033[0m" if sllm.common.use_color() else "", end="\n")

    return is_ok(review)


def app() -> None:
    parser = argparse.ArgumentParser()
    flags = parser.add_mutually_exclusive_group()
    flags.add_argument("--ref", help="load from commit", type=str)
    flags.add_argument("--file", help="load from file", type=pathlib.Path)
    parser.add_argument("--debug", action="store_true", help="nerd information")

    args = parser.parse_args()

    message: str
    if args.ref is not None:
        message = read_from_ref(args.ref)
    elif args.file is not None:
        message = read_from_file(args.file)
    else:
        parser.print_help()
        return

    if not len(message):
        logger.info("The message is empty.")
        return

    sllm.container.ensure_runtime()
    sllm.container.ensure_started()
    sllm.container.schedule_shutdown()

    communicate_request(message)

    logger.info("Rating...")
    request = sllm.api.Request(
        prompt=(
            importlib.resources.files("_sllm_git_message")
            .joinpath("prompt.txt")
            .read_text()
        ),
        query=message,
        example_input_header="[Instruction]",
        example_response_header="[Review]",
    )
    response: dict = request.send()
    review: str = response["choices"][0]["message"]["content"].strip()
    ok: bool = communicate_response(review)
    if not ok:
        logger.warning("You should use '--amend' to rewrite the message.")


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
            print(exc)
        return 1
