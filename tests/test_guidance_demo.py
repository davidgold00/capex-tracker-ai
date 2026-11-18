import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["demo"], "Chart:"),
        (["demo-guard"], "REJECT:"),
        (["explain", "ID=META-6e73e0ba7afe"], "Clean document SHA-256"),
    ],
)
def test_make_targets_offline(args, expected, tmp_path):
    (tmp_path / "sitecustomize.py").write_text(
        "import socket\n"
        "def denied(*a, **k): raise AssertionError('offline only')\n"
        "socket.socket.connect = denied\n"
    )
    # Make adds the project source to PYTHONPATH; retain sitecustomize via PYTHON's wrapper.
    import shlex

    interpreter = tmp_path / "offline-python"
    interpreter.write_text(
        "#!/bin/sh\nexport PYTHONPATH="
        + shlex.quote(str(tmp_path))
        + ":$PYTHONPATH\nexec "
        + shlex.quote(sys.executable)
        + ' "$@"\n'
    )
    interpreter.chmod(0o700)
    result = subprocess.run(
        ["make", *args],
        env={**os.environ, "PYTHON": str(interpreter)},
        capture_output=True,
        text=True,
        timeout=100,
        check=True,
    )
    assert expected in result.stdout
