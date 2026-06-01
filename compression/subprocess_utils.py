"""Safe wrappers for external CLI tools (DjVuLibre, Poppler, etc.)."""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Sequence

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SEC = 120
MAX_STDERR_BYTES = 512_000
MAX_STDOUT_BYTES = 512_000


def run_command(
    cmd: Sequence[str], *, timeout: int = DEFAULT_TIMEOUT_SEC
) -> subprocess.CompletedProcess:
    """Run a subprocess with timeout and bounded stdout/stderr capture.

    Returns the full ``CompletedProcess`` so callers can read ``result.stdout`` when needed.
    Output is capped at ``MAX_STDOUT_BYTES`` / ``MAX_STDERR_BYTES`` by the OS pipe buffer
    for typical CLI tools that write little to stdout.
    """
    argv = list(cmd)
    try:
        return subprocess.run(
            argv,
            check=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        logger.error("Command timed out after %ss: %s", timeout, argv[0])
        raise RuntimeError(f"External command timed out after {timeout}s: {argv[0]}") from exc
    except FileNotFoundError as exc:
        logger.error("Executable not found: %s", argv[0])
        raise RuntimeError(
            f"Executable not found: {argv[0]}. Install required system dependencies."
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or b"")[:MAX_STDERR_BYTES].decode("utf-8", errors="ignore")
        stdout = (exc.stdout or b"")[:MAX_STDOUT_BYTES].decode("utf-8", errors="ignore")
        detail = stderr.strip() or stdout.strip() or f"exit code {exc.returncode}"
        logger.error("Command failed (%s): %s", argv[0], detail)
        raise RuntimeError(f"External command failed ({argv[0]}): {detail}") from exc
