import argparse
import datetime
import json
import subprocess
import sys
import logging
import traceback

import sllm.common
import sllm.container


logger = logging.getLogger(__name__)


def _status_runtime() -> None:
    cmd = ["podman", "image", "ls", "--format", "json"]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode > 0:
        logger.error(f"Cannot query for runtime: {proc.stderr}.")
        return

    images: list[dict] = json.loads(proc.stdout)
    for image in images:
        if "quay.io/ramalama/ramalama:latest" in image.get("Names", []):
            break
    else:
        logger.info("Runtime is not present.")
        return

    logger.info(
        "Runtime is present ({size:.2f} GB).".format(
            size=image["Size"] / 2**30,
        )
    )


def _status_model() -> None:
    cmd = ["ramalama", "ls", "--json"]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode > 0:
        logger.error(f"Cannot query for models: {proc.stderr}.")
        return

    models: list[dict] = json.loads(proc.stdout)
    for model in models:
        if sllm.container.MODEL in model["name"]:
            break
    else:
        logger.info("Model is not present.")
        return

    logger.info(
        "Model is present ({size:.2f} GB).".format(
            size=model["size"] / 2**30,
        )
    )


def _status_api() -> None:
    cmd = ["ramalama", "ps", "--format", "json"]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode > 0:
        logger.error(f"Cannot query for API: {proc.stderr}.")
        return

    models: list[dict] = json.loads(proc.stdout)
    for model in models:
        if sllm.container.MODEL in model["Labels"]["ai.ramalama.model"]:
            break
    else:
        logger.info("API is not running.")
        return

    logger.info(f"API is present (http://127.0.0.1:{sllm.common.API_PORT}).")


def _status_shutdown() -> None:
    cmd = ["systemctl", "--user", "list-timers", "--output", "json"]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode > 0:
        logger.error(f"Cannot query for timers: {proc.stderr}.")
        return

    timers: list[dict] = json.loads(proc.stdout)
    for timer in timers:
        if timer["unit"] == f"{sllm.container.SHUTDOWN_NAME}.timer":
            break
    else:
        logger.info("Container shutdown is not scheduled.")
        return

    at = datetime.datetime.fromtimestamp(timer["next"] // 10**6)
    logger.info(
        "Container shutdown is scheduled ({ts}).".format(
            ts=at.strftime("%Y-%m-%d %H:%M:%S"),
        )
    )


def status() -> None:
    _status_runtime()
    _status_model()
    _status_api()
    _status_shutdown()


def app() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true", help="ensure runtime")
    parser.add_argument("--status", action="store_true", help="runtime status")
    parser.add_argument("--debug", action="store_true", help="nerd information")

    args = parser.parse_args()
    if args.init:
        sllm.container.ensure_runtime()
        return
    if args.status:
        status()
        return

    parser.print_help()


def main() -> int:
    debug: bool = "--debug" in sys.argv
    sllm.common.configure_logging(debug=debug)

    try:
        app()
        return 0
    except Exception as exc:
        logger.critical(
            f"Aborting on unhandled exception {exc.__class__.__name__}."
        )
        if debug:
            traceback.print_exc()
        else:
            print(exc)
        return 1
