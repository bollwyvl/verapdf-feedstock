import os
import sys
import subprocess
import zipfile
import tempfile
import shutil
import textwrap
import stat
from pprint import pprint
from pathlib import Path
import platform

UTF8 = dict(encoding="utf-8")
EXE_NAMES = ["verapdf", "verapdf-gui"]

CI = os.environ.get("CI")

WIN = platform.system() == "Windows"
INSTALL_SCRIPT = "verapdf-install.bat" if WIN else "verapdf-install"
RG_PATH = Path(r"C:\Miniforge\Library\bin\rg.exe")

SRC_DIR = Path(os.environ["SRC_DIR"])
PKG_VERSION = os.environ["PKG_VERSION"]
PREFIX = Path(os.environ["PREFIX"])
DEST = PREFIX / ("Library/verapdf" if WIN else "share/verapdf")

WHICH_MAVEN = (
    shutil.which("mvn")
    or shutil.which("mvn.exe")
    or shutil.which("mvn.bat")
    or shutil.which("mvn.cmd")
)

if not WHICH_MAVEN:
    sys.exit(1)

MVN_EXE = Path(WHICH_MAVEN)
MVN_OPTS = [str(MVN_EXE), "--batch-mode"]

WIN_TEMPLATE = """
@echo off
call "{script_src}" %*
"""


def mvn(args) -> int:
    final_args = list(map(str, [*MVN_OPTS, *args]))
    print(">>>", "\t".join(final_args), flush=True)
    rc = subprocess.call(final_args)
    if rc:
        sys.exit(rc)
    print("...  OK", "\t".join(final_args), flush=True)
    return rc


def build() -> int:
    return (
        mvn(["versions:set", f"-DnewVersion={PKG_VERSION}"])
        or mvn(["clean"])
        or mvn(["install", "-DskipTests"])
    )


def show(msg: str, path: Path) -> None:
    print(f"{msg}... {path}", "\n")
    print(textwrap.indent(path.read_text(**UTF8), "\t\t"), flush=True)


def install() -> int:
    src_auto_install = SRC_DIR / "auto-install-tmp.xml"

    zip_name = f"verapdf-greenfield-{PKG_VERSION}-installer.zip"

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        zip_path = SRC_DIR / "installer/target" / zip_name
        print("... extracting", zip_path)
        print("   -->", td, flush=True)
        with zipfile.ZipFile(str(zip_path)) as zf:
            zf.extractall(td)
        pprint(sorted(tdp.rglob("*")))
        inst_dir = tdp / f"verapdf-greenfield-{PKG_VERSION}"
        tmp_auto_install = inst_dir / "auto-install.xml"
        print("... updating", tmp_auto_install, flush=True)
        tmp_auto_install.write_text(
            src_auto_install.read_text(**UTF8).replace(
                "/tmp/verapdf",
                DEST.resolve().as_posix(),
            ),
            **UTF8,
        )
        show("... wrote", tmp_auto_install)

        script = inst_dir / INSTALL_SCRIPT

        str_args = [*map(str, [script, tmp_auto_install.name])]
        print(">>> ", str_args, flush=True)
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        rc = subprocess.call(str_args, cwd=str(inst_dir))
        if rc:
            sys.exit(rc)
        return rc


def deploy() -> int:
    for exe_name in EXE_NAMES:
        if WIN:
            script_src = DEST / f"{exe_name}.bat"
            script_dest = PREFIX / "Scripts" / script_src.name
        else:
            script_src = DEST / exe_name
            script_dest = PREFIX / "bin" / script_src.name

        script_dest.parent.mkdir(parents=True, exist_ok=True)

        print("... linking", script_src)
        print("   -->", script_dest)

        if WIN:
            make_bat_wrapper(script_src, script_dest)
        else:
            script_dest.symlink_to(script_src)
    return 0


def make_bat_wrapper(script_src: Path, script_dest: Path) -> int:
    script_dest.write_text(WIN_TEMPLATE.format(script_src=str(script_src.resolve())))
    return 0


def clean() -> int:
    for path in [DEST / "Uninstaller"]:
        print("... cleaning", path, flush=True)
        shutil.rmtree(path)

    if CI and WIN and RG_PATH.exists():
        print(
            "... removing ripgrep for https://github.com/conda/conda-build/issues/4357"
        )
        RG_PATH.unlink()
    return 0


def main() -> int:
    build()
    install()
    deploy()
    clean()
    return 0


if __name__ == "__main__":
    sys.exit(
        build()
        or install()
        or deploy()
        or clean()
    )
