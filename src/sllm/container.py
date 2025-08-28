import logging
import os
import subprocess
import time
import json

import requests

import sllm.common


IMAGE: str = os.getenv("SLLM_OLLAMA", "docker.io/ollama/ollama:latest")
NAME: str = "sllm"
SHUTDOWN_NAME: str = "sllm-shutdown"
SHUTDOWN_INTERVAL: str = os.getenv("SLLM_SHUTDOWN_INTERVAL", "15m")

logger = logging.getLogger(__name__)


def ensure_runtime() -> None:
    """Download the ollama container.

    :raises RuntimeError: 'podman pull' failed.
    """
    logger.debug(f"Downloading '{IMAGE}'.")
    cmd_ollama = ["podman", "pull", IMAGE]
    proc_ollama = subprocess.run(cmd_ollama, text=True, capture_output=True)
    if proc_ollama.returncode > 0:
        logger.critical(f"'podman pull' returned {proc_ollama.returncode}.")
        raise RuntimeError(f"Couldn't pull '{IMAGE}'.")

    if not started():
        start()
        wait_for_start()
        schedule_shutdown()

    logger.debug(f"Downloading '{sllm.common.MODEL}'.")

    cmd_model = ["podman", "exec", "-it", NAME]
    cmd_model += ["ollama", "pull", sllm.common.MODEL]
    proc = subprocess.run(cmd_model, text=True, capture_output=True)
    if proc.returncode > 0:
        logger.critical(f"'ollama pull' returned {proc.returncode}.")
        raise RuntimeError(f"Couldn't pull model '{sllm.common.MODEL}'.")
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
        resp = requests.get(f"{sllm.common.API_URL}/")
    except Exception as exc:
        logger.debug(f"HTTP API is not running: {exc}.")
        return False

    if not resp.ok:
        logger.debug("HTTP API is not well.")
        return False

    logger.debug("Runtime is running.")
    return True


def start() -> None:
    """Start the ramalama server.

    :raises RuntimeError:
    """
    cmd = ["podman", "run"]
    # cmd += ["--gpus", "all"]  # This errors out without Nvidia GPU
    cmd += ["--detach"]
    cmd += ["--rm"]
    cmd += ["--volume", "ollama:/root/.ollama"]
    cmd += ["--publish", f"{str(sllm.common.API_PORT)}:11434"]
    cmd += ["--name", NAME]
    cmd += [IMAGE]

    logger.info("Starting the container.")
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode > 0:
        logger.debug(f"Command {cmd} failed: {proc.stderr.strip()}")
        raise RuntimeError("Server could not be started.")


def wait_for_start() -> None:
    """Wait for the server to start.

    :raises TimeoutError: Server didn't start on time.
    """
    for _ in range(10):
        time.sleep(0.5)
        if started():
            logger.debug("Server is now running.")
            return

    raise TimeoutError


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
