"""Regression tests for ClawBench's Harbor integration."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HARBOR_AGENT_WRAPPER = (
    REPO_ROOT / "src" / "clawbench" / "runtime" / "harbor" / "wrap-harbor-agent.sh"
)


@pytest.mark.skipif(
    sys.platform != "linux",
    reason="wrap-harbor-agent.sh runs inside Harbor's Linux containers; "
    "bash signal handling differs on mac and windows runners",
)
def test_stop_wrapper_interrupts_agent_and_exits_cleanly(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_agent = bin_dir / "claude"
    started = tmp_path / "started"
    stop_file = tmp_path / "stop-requested"
    stop_result = tmp_path / "agent-stop.json"
    fake_agent.write_text(
        "#!/bin/bash\n"
        "trap 'exit 130' INT\n"
        'touch "$FAKE_AGENT_STARTED"\n'
        "while true; do sleep 0.1; done\n"
    )
    fake_agent.chmod(0o755)
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "FAKE_AGENT_STARTED": str(started),
        "CLAWBENCH_STOP_FILE": str(stop_file),
        "CLAWBENCH_STOP_RESULT": str(stop_result),
    }

    subprocess.run([HARBOR_AGENT_WRAPPER, "claude"], env=env, check=True)
    process = subprocess.Popen([fake_agent], env=env)
    deadline = time.monotonic() + 2
    while not started.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert started.exists()

    stop_file.touch()
    assert process.wait(timeout=3) == 0
    assert json.loads(stop_result.read_text())["signal"] == "INT"
