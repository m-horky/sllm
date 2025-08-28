import argparse
import datetime
import json
import subprocess
import sys
import logging
import traceback

import requests

import sllm.common
import sllm.container


logger = logging.getLogger(__name__)


def _status_runtime() -> None:
    # Check if this image is present in podman
    query_cmd = ["podman", "image", "ls", "--format", "json"]
    proc = subprocess.run(query_cmd, text=True, capture_output=True)
    if proc.returncode > 0:
        logger.error(f"Cannot query for runtime: {proc.stderr.strip()}")
        return

    images: list[dict] = json.loads(proc.stdout)
    for image in images:
        if sllm.container.IMAGE in image.get("Names", []):
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
    try:
        resp = requests.get(f"{sllm.common.API_URL}/api/tags")
    except Exception as exc:
        logger.info("HTTP API is not running, models not accessible.")
        logger.debug(f"HTTP API is not running: {exc}.")
        return

    if not resp.ok:
        logger.info("HTTP API is not running, models not accessible.")
        logger.debug(f"HTTP API is not well: {resp}.")
        return

    for model in resp.json().get("models"):
        if sllm.common.MODEL in model["name"]:
            break
    else:
        logger.info("Model is not present.")
        return

    logger.info(
        "Model is present ({quant}, {size:.2f} GB).".format(
            quant=model["details"]["quantization_level"],
            size=model["size"] / 2**30,
        )
    )


def _status_api() -> None:
    try:
        resp = requests.get(f"{sllm.common.API_URL}/api/version")
    except Exception as exc:
        logger.info("HTTP API is not running.")
        logger.debug(f"HTTP API is not running: {exc}.")
        return

    if not resp.ok:
        logger.info("HTTP API is not running.")
        logger.debug(f"HTTP API is not well: {resp}.")
        return

    version: str = resp.json().get("version", "unknown")
    logger.info(
        f"API is present (http://127.0.0.1:{sllm.common.API_PORT}, "
        f"version {version})."
    )


def _status_shutdown() -> None:
    cmd = ["systemctl", "--user", "list-timers", "--output", "json"]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode > 0:
        logger.error(f"Cannot query for timers: {proc.stderr.strip()}")
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
    _status_api()
    _status_model()
    _status_shutdown()


def app() -> None:
    parser = argparse.ArgumentParser()
    flags = parser.add_mutually_exclusive_group()
    flags.add_argument("--init", action="store_true", help="ensure runtime")
    flags.add_argument("--status", action="store_true", help="runtime status")
    flags.add_argument("--start", action="store_true", help="start the runtime")
    flags.add_argument("--stop", action="store_true", help="stop the runtime")
    parser.add_argument("--debug", action="store_true", help="nerd information")

    args = parser.parse_args()
    if args.init:
        sllm.container.ensure_runtime()
        return
    if args.status:
        status()
        return
    if args.start:
        sllm.container.ensure_runtime()
        sllm.container.ensure_started()
        sllm.container.schedule_shutdown()
        print(f"Server is present at http://127.0.0.1:{sllm.common.API_PORT}.")
        return
    if args.stop:
        sllm.container._cancel_scheduled_shutdown()
        if sllm.container.started():
            sllm.container.shutdown()
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
