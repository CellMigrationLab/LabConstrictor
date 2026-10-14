"""Smoke install of the template's post_install script: the installed registry entry carries the hosts of the app's labconstrictor-app.yaml.

Runs the LIVE post_install.sh (Linux, macOS) or post_install.bat (Windows) of the template for real, in a fake install prefix (a venv with
the app package `demoapp` and its tools module `demoapp_lc_tools`) with the real labconstrictor-tools installed by the script itself
(LC_TOOLS_SPEC, or the pinned tag when it is not set), then reads the registry entry `<LC_HOME>/apps/DemoApp.json`.

Cases: the real manifests of the apps (tests/fixtures/manifests), a manifest without a hosts: line and no manifest at all. For each, the `hosts`
of the entry must equal the `hosts:` line of the manifest (in the declared order), and for the last two the entry must have no `hosts` and
the installer log must carry the sentence "declares no hosts". Anything else is a failure, never a skip.

What is stood in for (the rest is the real script): the TLS launcher (prints a CA bundle, answers --self-test), include_path.py,
hide_code_cells.py and menuinst (no shortcuts), and on Windows the venv layout (python is in Scripts\\, so the script's PYTHON_EXE line is pointed there).

Usage: python tests/smoke/post_install_hosts.py     (env: LC_TOOLS_SPEC optional; SMOKE_CA_BUNDLE optional, a CA file for pip behind a proxy)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "app/bash_bat_scripts"
MANIFESTS = ROOT / "tests/fixtures/manifests"
WINDOWS = os.name == "nt"
APP = "DemoApp"
NO_HOSTS = "declares no hosts, so it is listed in every host"
TOKENS = (
    ("UNDERSCORED_PROJECT_NAME", "Demo_App"),
    ("PYTHON_PROJ_NAME", "demoapp"),
    ("PROJECT_NAME", APP),
    ("VERSION_NUMBER", "1.2.3"),
    ("GITHUB_OWNER", "CellMigrationLab"),
)
SETUP_PY = 'from setuptools import find_packages, setup\nsetup(name="demoapp", version="1.2.3", package_dir={"": "src"}, packages=find_packages("src"))\n'
TOOLS_MODULE = (
    "from labconstrictor_tools import Scalars, tool\n\n\n"
    '@tool("Double a number")\n'
    "def double(x: float = 2.0) -> Scalars:\n"
    '    return {"y": x * 2}\n'
)
LAUNCHER = (
    "import sys\n"
    "if '--print-ca-bundle' in sys.argv:\n"
    "    import os\n"
    "    from pip._vendor import certifi\n"
    "    print(os.environ.get('SMOKE_CA_BUNDLE') or certifi.where())\n"
)
MENUINST_API = "def install(path):\n    return path\n"
HOSTS_LINE = re.compile(r"(?m)^hosts[ \t]*:[ \t]*\[(.*)\]")


def venv_python(prefix: Path) -> Path:
    return prefix / ("Scripts/python.exe" if WINDOWS else "bin/python")


def declared_hosts(manifest: Path) -> list[str]:
    """The names of the `hosts: [a, b]` line of a manifest, in order (the fixtures write it as a flow list)."""
    match = HOSTS_LINE.search(manifest.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"{manifest} has no hosts: [..] line")
    return [name.strip() for name in match.group(1).split(",") if name.strip()]


def run(command: list[str], env: dict[str, str] | None = None, stdin: int | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True, env=env, stdin=stdin)


def make_prefix(base: Path) -> Path:
    """A fake install prefix: a venv with setuptools, a stub menuinst, and the project folder of the app (DemoApp) without a manifest."""
    prefix = base / "prefix"
    run([sys.executable, "-m", "venv", str(prefix)])
    python = str(venv_python(prefix))
    ca = os.environ.get("SMOKE_CA_BUNDLE")
    extra = ["--cert", ca] if ca else []
    run([python, "-m", "pip", "install", "--quiet", "pip>=24.2", "setuptools>=70.1", "wheel", *extra])
    site = Path(subprocess.check_output([python, "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"], text=True).strip())
    (site / "menuinst").mkdir()
    (site / "menuinst/__init__.py").write_text("", encoding="utf-8")
    (site / "menuinst/api.py").write_text(MENUINST_API, encoding="utf-8")
    write_project(prefix / APP)
    return prefix


def write_project(root: Path) -> None:
    (root / "src/demoapp").mkdir(parents=True)
    (root / "src/demoapp_lc_tools").mkdir(parents=True)
    (root / "src/demoapp/__init__.py").write_text("", encoding="utf-8")
    (root / "src/demoapp_lc_tools/__init__.py").write_text(TOOLS_MODULE, encoding="utf-8")
    (root / "setup.py").write_text(SETUP_PY, encoding="utf-8")
    (root / "launch_jupyter.py").write_text(LAUNCHER, encoding="utf-8")
    for helper in ("include_path.py", "hide_code_cells.py"):
        (root / helper).write_text("", encoding="utf-8")
    (root / "requirements.txt").write_text("setuptools\n", encoding="utf-8")
    (root / "construct.yaml").write_text("name: Demo_App\nversion: 1.2.3\n", encoding="utf-8")
    (root / "notebook_launcher.json").write_text("{}", encoding="utf-8")


def render_script(base: Path) -> Path:
    """The live script of this OS with the app's names filled in (on Windows also pointed at the venv's python)."""
    name = "post_install.bat" if WINDOWS else "post_install.sh"
    text = (SCRIPTS / name).read_bytes().decode().replace("\r\n", "\n")
    for token, value in TOKENS:
        text = text.replace(token, value)
    if WINDOWS:
        text = text.replace('SET "PYTHON_EXE=%PREFIX%\\python.exe"', 'SET "PYTHON_EXE=%PREFIX%\\Scripts\\python.exe"')
        text = text.replace("\n", "\r\n")
    path = base / name
    path.write_bytes(text.encode())
    return path


def install(script: Path, prefix: Path, lc_home: Path) -> str:
    """Run the script as the installer does (PREFIX in the environment); return the installer log."""
    env = {**os.environ, "PREFIX": str(prefix), "LC_HOME": str(lc_home)}
    command = ["cmd", "/c", str(script)] if WINDOWS else ["bash", str(script)]
    log_file = prefix / "menuinst_debug.log"
    try:
        run(command, env=env, stdin=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("The installer failed; its log:\n" + log_file.read_text(encoding="utf-8", errors="replace"), flush=True)
        raise
    return log_file.read_text(encoding="utf-8", errors="replace")


def registry_entry(lc_home: Path) -> dict[str, object]:
    path = lc_home / "apps" / f"{APP}.json"
    if not path.is_file():
        raise AssertionError(f"no registry entry at {path}")
    entry: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
    return entry


def check_declared(name: str, manifest: Path, entry: dict[str, object], log: str) -> None:
    expected = declared_hosts(manifest)
    if entry.get("hosts") != expected:
        raise AssertionError(f"{name}: registry hosts {entry.get('hosts')!r} != hosts line of the manifest {expected!r}")
    warnings = [line for line in log.splitlines() if "WARNING" in line and "conda" not in line]  # the stand-in prefix has no conda
    if warnings:
        raise AssertionError(f"{name}: the installer log has a WARNING: {warnings}")
    print(f"OK {name}: hosts {expected}", flush=True)


def check_undeclared(name: str, entry: dict[str, object], log: str) -> None:
    if "hosts" in entry:
        raise AssertionError(f"{name}: the entry must have no hosts, it has {entry['hosts']!r}")
    if f"'{APP}' {NO_HOSTS}" not in log.replace("^", ""):
        raise AssertionError(f"{name}: the installer log does not say that the app declares no hosts:\n{log}")
    print(f"OK {name}: no hosts, and the log says so", flush=True)


def install_case(script: Path, prefix: Path, lc_home: Path) -> tuple[dict[str, object], str]:
    """Install once into a fresh registry home: (the registry entry of the app, the installer log)."""
    log = install(script, prefix, lc_home)
    return registry_entry(lc_home), log


def main() -> int:
    manifests = sorted(MANIFESTS.glob("*_labconstrictor-app.yaml"))
    if len(manifests) < 5:
        raise AssertionError(f"expected the real manifests of the apps in {MANIFESTS}, found {len(manifests)}")
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        prefix = make_prefix(base)
        script = render_script(base)
        target = prefix / APP / "labconstrictor-app.yaml"
        for manifest in manifests:
            target.write_bytes(manifest.read_bytes())
            entry, log = install_case(script, prefix, base / f"home_{manifest.stem}")
            check_declared(manifest.name, manifest, entry, log)
        target.write_text("schema: 1\nname: Demo\n", encoding="utf-8")
        entry, log = install_case(script, prefix, base / "home_no_hosts_line")
        check_undeclared("manifest without a hosts: line", entry, log)
        target.unlink()
        entry, log = install_case(script, prefix, base / "home_no_manifest")
        check_undeclared("no manifest in the install", entry, log)
    print("post_install hosts smoke: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
