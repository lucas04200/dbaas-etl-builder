"""
Tests for docker_remove() in provisioning.py.

Verifies that:
1. 'docker kill' is called before 'docker rm --force'
2. A kill failure does NOT prevent 'docker rm --force' from running
3. Volumes are removed after the container
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.api.services.provisioning import docker_remove


def _make_proc(returncode: int, stderr: bytes = b""):
    """Build a mock async process returned by create_subprocess_exec."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(b"", stderr))
    return proc


@pytest.mark.asyncio
async def test_docker_remove_calls_kill_then_force_rm():
    """docker kill must be called, then docker rm --force."""
    procs = [
        _make_proc(0),   # docker kill → success
        _make_proc(0),   # docker rm --force → success
    ]
    with patch(
        "app.api.services.provisioning.asyncio.create_subprocess_exec",
        side_effect=procs,
    ) as mock_exec:
        await docker_remove("my_container")

    calls = mock_exec.call_args_list
    assert calls[0] == call("docker", "kill", "my_container",
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.PIPE)
    assert calls[1] == call("docker", "rm", "--force", "my_container",
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.PIPE)


@pytest.mark.asyncio
async def test_docker_remove_rm_force_runs_even_if_kill_fails():
    """A permission-denied kill must not block force-remove (the real-world bug)."""
    procs = [
        _make_proc(1, b"permission denied"),  # docker kill → fails
        _make_proc(0),                        # docker rm --force → success
    ]
    with patch(
        "app.api.services.provisioning.asyncio.create_subprocess_exec",
        side_effect=procs,
    ) as mock_exec:
        await docker_remove("zombie_container")   # must not raise

    assert mock_exec.call_count == 2
    # Second call must be rm --force
    assert mock_exec.call_args_list[1][0][1] == "rm"
    assert "--force" in mock_exec.call_args_list[1][0]


@pytest.mark.asyncio
async def test_docker_remove_with_volumes():
    """Volumes must be removed after the container."""
    procs = [
        _make_proc(0),  # docker kill
        _make_proc(0),  # docker rm --force
        _make_proc(0),  # docker volume rm vol1
        _make_proc(0),  # docker volume rm vol2
    ]
    with patch(
        "app.api.services.provisioning.asyncio.create_subprocess_exec",
        side_effect=procs,
    ) as mock_exec:
        await docker_remove("my_container", volume_names=["vol1", "vol2"])

    assert mock_exec.call_count == 4
    assert mock_exec.call_args_list[2][0] == ("docker", "volume", "rm", "vol1")
    assert mock_exec.call_args_list[3][0] == ("docker", "volume", "rm", "vol2")


@pytest.mark.asyncio
async def test_docker_remove_no_volumes():
    """No volume calls when volume_names is None or empty."""
    procs = [_make_proc(0), _make_proc(0)]
    with patch(
        "app.api.services.provisioning.asyncio.create_subprocess_exec",
        side_effect=procs,
    ) as mock_exec:
        await docker_remove("my_container", volume_names=None)

    assert mock_exec.call_count == 2  # only kill + rm --force
