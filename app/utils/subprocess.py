from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class ProcessResult:
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool = False


async def run_command(
    command: str,
    *,
    cwd: str | None = None,
    timeout: float = 30.0,
    env: dict[str, str] | None = None,
) -> ProcessResult:
    """Run a shell command asynchronously with timeout."""
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return ProcessResult(
                stdout="",
                stderr=f"Command timed out after {timeout}s",
                returncode=-1,
                timed_out=True,
            )
        return ProcessResult(
            stdout=stdout_bytes.decode("utf-8", errors="replace"),
            stderr=stderr_bytes.decode("utf-8", errors="replace"),
            returncode=proc.returncode or 0,
        )
    except OSError as exc:
        return ProcessResult(stdout="", stderr=str(exc), returncode=-1)
