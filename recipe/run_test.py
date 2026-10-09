import platform
import shutil
import os
import sys

from subprocess import run, call, CompletedProcess, PIPE
from pathlib import Path

import pytest


WIN = platform.system() == "Windows"
SCRIPT_EXT = ".bat" if WIN else ""
PKG_VERSION = os.environ["PKG_VERSION"]
SHARE_DOCS = Path(sys.prefix) / ("Library" if WIN else "share") / "verapdf/documents"
PYTEST_ARGS = [sys.executable, "-m", "pytest", "-vv", "--color=yes", __file__]


def _find_cmd(cmd: str) -> str:
    found = shutil.which(f"{cmd}{SCRIPT_EXT}")
    if not found:
        raise FileNotFoundError(cmd)
    return found


def _verapdf(
    *args: str | Path,
    check_stdout: str,
    check_empty_stderr: bool = True,
    check_rc: int = 0,
    cwd: Path | None = None,
) -> CompletedProcess[str]:
    str_args = list(map(str, ["verapdf", *args]))
    print(">>>", *str_args, flush=True)
    res: CompletedProcess = run(
        " ".join(str_args),
        stdout=PIPE,
        stderr=PIPE,
        encoding="utf-8",
        cwd=str(cwd) if cwd else None,
        shell=True,
    )
    rc, out, err = res.returncode, res.stdout, res.stderr
    print("\n\n".join(["STDOUT", out, "STDERR", err, "RC", f"{rc}"]))
    assert check_stdout in out
    if check_empty_stderr:
        assert not err
    assert rc == check_rc
    return res


@pytest.mark.parametrize("cmd", ["verapdf", "verapdf-gui"])
def test_cmd_exists(cmd: str) -> None:
    assert Path(_find_cmd(cmd)).exists()


def test_cmd_help() -> None:
    _verapdf("--help", check_stdout=PKG_VERSION)


def test_cmd_version() -> None:
    _verapdf("--version", check_stdout=PKG_VERSION)


@pytest.mark.parametrize(
    ("expect_rc", "expect_stdout", "docname"),
    [
        (1, "FAIL", "veraPDFPDFAConformanceCheckerGUI.pdf"),
        (0, "PASS", "Matterhorn-Protocol-1-1.pdf"),
    ],
)
def test_cmd_validate(
    tmp_path: Path, expect_rc: int, expect_stdout: str, docname: str
) -> None:
    doc = SHARE_DOCS / docname
    shutil.copy2(doc, tmp_path / doc.name)
    _verapdf(
        "--format",
        "text",
        "--flavour",
        "ua1",
        doc.name,
        check_rc=expect_rc,
        check_stdout=expect_stdout,
        cwd=tmp_path,
    )


if __name__ == "__main__":
    sys.exit(call(PYTEST_ARGS, encoding="utf-8"))
