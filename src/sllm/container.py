import logging
import os
import subprocess
import time
import json

import requests

import sllm.common


MODEL: str = os.getenv("SLLM_MODEL", "ollama://llama3.2:3b")
RUNTIME: str = os.getenv("SLLM_RAMALAMA", "")
NAME: str = "sllm"
SHUTDOWN_NAME: str = "sllm-shutdown"
SHUTDOWN_INTERVAL: str = os.getenv("SLLM_SHUTDOWN_INTERVAL", "15m")

logger = logging.getLogger(__name__)


def ensure_runtime() -> None:
    """Download the ramalama runtime and the model.

    :raises RuntimeError: 'ramalama pull' failed.
    """
    logger.debug(f"Downloading '{MODEL}'.")

    cmd = ["ramalama"]
    if RUNTIME:
        logger.debug(f"Using custom ramalama image {RUNTIME}.")
        cmd += ["--image", RUNTIME]
    cmd += ["pull", MODEL]
    proc = subprocess.run(cmd, text=True, capture_output=False)
    if proc.returncode > 0:
        logger.critical(f"'ramalama pull' returned {proc.returncode}.")
        raise RuntimeError(f"Couldn't pull model '{MODEL}'.")
    logger.debug("Downloaded.")


def ensure_started() -> None:
    """Start the ramalama server.

    Does nothing if the server is already running.

    :raises TimeoutError: Server did not start fast enough.
    """
    if started():
        return

    start()

    for _ in range(10):
        time.sleep(0.5)
        if started():
            logger.debug("Server is now running.")
            return

    raise TimeoutError


def started() -> bool:
    """Query the ramalama server for status.

    :returns: True if ramalama is ready to serve requests.
    """
    cmd = ["podman", "inspect", NAME]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode > 0:
        logger.debug("Container is not running.")
        return False

    status: str = (
        json.loads(proc.stdout)[0].get("State", {}).get("Status", "unknown")
    )
    if status != "running":
        logger.debug(f"Container is running in unexpected state of '{status}'.")
        return False

    try:
        resp = requests.get(f"{sllm.common.API_URL}/health")
    except Exception as exc:
        logger.debug(f"HTTP API is not running: {exc}.")
        return False

    if not resp.ok:
        logger.debug("Model is not running.")
        return False

    logger.debug("Container, ramalama and model are running.")
    return True


def start() -> None:
    """Start the ramalama server.

    :raises RuntimeError:
    """
    cmd = ["ramalama"]
    if RUNTIME:
        cmd += ["--image", RUNTIME]
    cmd += ["serve"]
    # Decrease context size
    cmd += ["--ctx-size", "2048"]
    # Do not download if not necessary
    cmd += ["--pull", "missing"]
    # Configure
    cmd += ["--port", str(sllm.common.API_PORT)]
    cmd += ["--name", NAME]
    cmd += ["--detach"]
    cmd += [MODEL]

    logger.info("Starting the container.")
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode > 0:
        logger.debug(f"Command {cmd} failed: {proc.stderr.strip()}")
        raise RuntimeError("Server could not be started.")


def _cancel_scheduled_shutdown() -> None:
    """Cancel the scheduled container shutdown."""
    cmd = ["systemctl", "--user", "stop", f"{SHUTDOWN_NAME}.timer"]

    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode == 0:
        logger.debug("Scheduled shutdown has been cancelled.")
    # Non-zero exit code means there was no timer scheduled.


def schedule_shutdown() -> None:
    """Schedule the container to shut down.

    Sets a systemd timer to stop the container. Consecutive execution
    will cancel the previous timer and set up a new one.
    """
    _cancel_scheduled_shutdown()

    cmd = ["systemd-run", "--user"]
    cmd += ["--unit", SHUTDOWN_NAME]
    cmd += ["--on-active", SHUTDOWN_INTERVAL]
    cmd += ["podman", "stop", NAME]

    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode > 0:
        logger.warning(f"Cannot schedule shutdown: {proc.stderr.strip()}")
        return
    logger.debug("Container shutdown has been scheduled.")


def shutdown() -> None:
    """Shut down the container."""
    cmd = ["podman", "stop", NAME]

    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode > 0:
        logger.warning(f"Container cannot be shut down: {proc.stderr.strip()}")
        return
    logger.debug("Container has been shut down.")
