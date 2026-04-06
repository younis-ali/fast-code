from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Active PTY sessions: token -> session dict
_sessions: dict[str, dict[str, Any]] = {}


@router.websocket("/ws")
async def websocket_terminal(ws: WebSocket):
    """WebSocket endpoint for interactive terminal sessions.

    Protocol:
    - Client sends JSON {"type": "resize", "cols": N, "rows": N} for terminal resize
    - Client sends plain text for terminal input
    - Server sends plain text for terminal output
    - Server sends JSON {"type": "session", "token": "..."} on connection
    """
    await ws.accept()

    if len(_sessions) >= settings.max_sessions:
        await ws.send_json({"type": "error", "message": "Maximum sessions reached"})
        await ws.close(code=1013)
        return

    token = f"pty_{uuid.uuid4().hex[:16]}"

    try:
        import ptyprocess
    except ImportError:
        await ws.send_json({"type": "error", "message": "ptyprocess not installed"})
        await ws.close(code=1011)
        return

    cwd = settings.work_dir or os.environ.get("HOME", "/tmp")
    shell = os.environ.get("SHELL", "/bin/bash")

    try:
        pty = ptyprocess.PtyProcessUnicode.spawn(
            [shell],
            cwd=cwd,
            env={
                **os.environ,
                "TERM": "xterm-256color",
                "COLORTERM": "truecolor",
            },
            dimensions=(24, 80),
        )
    except Exception as exc:
        logger.exception("Failed to spawn PTY")
        await ws.send_json({"type": "error", "message": str(exc)})
        await ws.close(code=1011)
        return

    _sessions[token] = {"pty": pty, "ws": ws}
    await ws.send_json({"type": "session", "token": token})

    # Background task: read PTY output and send to WebSocket
    async def read_pty():
        loop = asyncio.get_event_loop()
        try:
            while pty.isalive():
                try:
                    data = await loop.run_in_executor(None, lambda: pty.read(4096))
                    await ws.send_text(data)
                except EOFError:
                    break
                except Exception:
                    break
        finally:
            await ws.send_json({"type": "exit", "code": pty.exitstatus or 0})

    reader_task = asyncio.create_task(read_pty())

    try:
        while True:
            raw = await ws.receive_text()

            # Try JSON control messages
            try:
                msg = json.loads(raw)
                if isinstance(msg, dict) and msg.get("type") == "resize":
                    cols = msg.get("cols", 80)
                    rows = msg.get("rows", 24)
                    pty.setwinsize(rows, cols)
                    continue
                elif isinstance(msg, dict) and msg.get("type") == "ping":
                    await ws.send_json({"type": "pong"})
                    continue
            except (json.JSONDecodeError, ValueError):
                pass

            # Regular terminal input
            if pty.isalive():
                pty.write(raw)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session %s", token)
    except Exception:
        logger.exception("WebSocket error for session %s", token)
    finally:
        reader_task.cancel()
        if pty.isalive():
            pty.terminate(force=True)
        _sessions.pop(token, None)
