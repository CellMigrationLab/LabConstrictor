from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _project_folder(construct_text: str | None = None) -> str:
    text = construct_text or _read("construct.yaml")
    for pattern in (
        r"app/menuinst/Welcome\.ipynb:\s*([^\r\n/]+)/notebooks/Welcome\.ipynb",
        r"app/menuinst/notebook_launcher\.json:\s*([^\r\n/]+)/notebook_launcher\.json",
        r"requirements\.txt:\s*([^\r\n/]+)/requirements\.txt",
    ):
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    raise AssertionError("Unable to determine the constructor project folder")


def _python_package_name(setup_text: str | None = None) -> str:
    src_root = ROOT / "src"
    if setup_text is None and src_root.is_dir():
        candidates = sorted(
            child.name
            for child in src_root.iterdir()
            if child.is_dir()
            and child.name.isidentifier()
            and (child / "__init__.py").is_file()
        )
        if len(candidates) == 1:
            return candidates[0]

    text = setup_text or _read("setup.py")
    match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', text)
    if not match:
        raise AssertionError("Unable to determine the Python package name")
    return match.group(1).replace("-", "_")


def test_constructor_environment_avoids_automatic_certificate_injection() -> None:
    environment = yaml.safe_load(_read("environment.yaml"))
    dependencies = [str(item) for item in environment["dependencies"]]

    assert not any(item.startswith("pip-system-certs") for item in dependencies)
    assert any(item.startswith("pip>=24.2") for item in dependencies)
    assert "setuptools" in dependencies
    assert "wheel" in dependencies
    assert "menuinst>=2" in dependencies
    assert "certifi" in dependencies
    assert any(item.startswith("truststore") for item in dependencies)


def test_constructor_bundles_tls_launcher() -> None:
    construct = _read("construct.yaml")
    project_folder = _project_folder(construct)
    assert f"app/python_scripts/launch_jupyter.py: {project_folder}/launch_jupyter.py" in construct


def test_windows_post_install_is_verified_fail_fast_and_package_optional() -> None:
    script = _read("app/bash_bat_scripts/post_install.bat")
    project_folder = _project_folder()
    package_name = _python_package_name()

    assert 'SET "PIP_USE_DEPRECATED=legacy-certs"' in script
    assert 'SET "PIP_CERT=%CA_BUNDLE%"' in script
    assert 'SET "REQUESTS_CA_BUNDLE=%CA_BUNDLE%"' in script
    assert 'SET "CURL_CA_BUNDLE=%CA_BUNDLE%"' in script
    assert '--print-ca-bundle' in script
    assert '-m pip install -r "%SELECTED_REQUIREMENTS%" >> "%LOG_FILE%" 2>&1' in script
    assert '-m pip install --no-deps --no-build-isolation "%PROJECT_ROOT%"' in script
    assert f"import {package_name};" in script
    assert 'IF EXIST "%PROJECT_ROOT%\\setup.py" (' in script
    assert '--set ssl_verify "%CA_BUNDLE%"' in script
    assert "ssl_verify truststore" not in script
    assert f'SET "PROJECT_ROOT=%PREFIX%\\{project_folder}"' in script
    assert "GOTO :fail" in script
    assert "EXIT /B 1" in script


def test_unix_post_install_matches_windows_safety_model() -> None:
    script = _read("app/bash_bat_scripts/post_install.sh")
    package_name = _python_package_name()

    assert "set -euo pipefail" in script
    assert "export PIP_USE_DEPRECATED=legacy-certs" in script
    assert 'export PIP_CERT="$CA_BUNDLE"' in script
    assert "--print-ca-bundle" in script
    assert '-m pip install --no-deps --no-build-isolation "$PROJECT_ROOT"' in script
    assert f"import {package_name};" in script
    assert '[ -f "$PROJECT_ROOT/setup.py" ]' in script
    assert '--set ssl_verify "$CA_BUNDLE"' in script
    assert "ssl_verify truststore" not in script


def test_launcher_has_verified_fallback_and_quiet_recovery_details() -> None:
    launcher = _read("app/python_scripts/launch_jupyter.py")

    assert '"LABCONSTRICTOR_CA_BUNDLE"' in launcher
    assert "_project_ca_bundle_environment_variable" in launcher
    assert "--print-ca-bundle" in launcher
    assert "context.verify_mode = ssl.CERT_REQUIRED" in launcher
    assert "context.check_hostname = True" in launcher
    assert "_write_log(note, console=False)" in launcher


def test_menu_launcher_uses_tls_resilient_python_entrypoint() -> None:
    launcher = json.loads(_read("app/menuinst/notebook_launcher.json"))
    command = launcher["menu_items"][0]["command"]

    assert command[0] == "{{ PYTHON }}"
    assert command[1].endswith("/launch_jupyter.py")
    assert command[2].endswith("/notebooks/Welcome.ipynb")


def test_template_manifest_registers_tls_hardening_migration() -> None:
    manifest = yaml.safe_load(_read(".template_sync/manifest.yaml"))

    assert manifest["template_version"] == "0.1.10"
    assert manifest["migrations"][-1] == {
        "from": "0.1.9",
        "to": "0.1.10",
        "script": "migrations/v0_1_9_to_v0_1_10.py",
    }


def test_tls_hardening_migration_renders_existing_projects(tmp_path: Path) -> None:
    repo = tmp_path / "example"
    (repo / "app/menuinst").mkdir(parents=True)
    (repo / "src/example_pkg").mkdir(parents=True)
    (repo / ".tools/docs").mkdir(parents=True)
    (repo / ".github/workflows").mkdir(parents=True)
    (repo / "tests").mkdir(parents=True)

    (repo / "environment.yaml").write_text(
        """name: example\nchannels:\n  - conda-forge\ndependencies:\n  - python=3.11\n  - pip\n  - pip-system-certs>=5.3\n  - jupyterlab=4.4.0\n""",
        encoding="utf-8",
    )
    (repo / "construct.yaml").write_text(
        """name: Example_App\nversion: 1.2.3\nicon_image: app/logo/logo.png\nextra_files:\n- app/menuinst/Welcome.ipynb: Example App/notebooks/Welcome.ipynb\n- app/menuinst/notebook_launcher.json: Example App/notebook_launcher.json\n- app/python_scripts/include_path.py: Example App/include_path.py\n- requirements.txt: Example App/requirements.txt\npost_install: app/bash_bat_scripts/post_install.bat # [win]\n""",
        encoding="utf-8",
    )
    (repo / "setup.py").write_text(
        'from setuptools import setup\nsetup(name="example-dist", package_dir={"": "src"})\n',
        encoding="utf-8",
    )
    (repo / "src/example_pkg/__init__.py").write_text("", encoding="utf-8")
    (repo / "app/menuinst/notebook_launcher.json").write_text(
        json.dumps(
            {
                "menu_items": [
                    {
                        "platforms": {
                            "win": {"icon": "BASE_PATH_KEYWORD/Example App/logo.ico"},
                            "linux": {"icon": "BASE_PATH_KEYWORD/Example App/logo.png"},
                            "osx": {"icon": "BASE_PATH_KEYWORD/Example App/logo.icns"},
                        }
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    migration_path = ROOT / ".template_sync/migrations/v0_1_9_to_v0_1_10.py"
    spec = importlib.util.spec_from_file_location("tls_migration", migration_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.migrate(repo_root=repo, context={})

    dependencies = [str(item) for item in yaml.safe_load((repo / "environment.yaml").read_text())["dependencies"]]
    assert not any(item.startswith("pip-system-certs") for item in dependencies)
    assert {"setuptools", "wheel", "menuinst>=2", "certifi"}.issubset(dependencies)
    assert any(item.startswith("truststore") for item in dependencies)

    construct = (repo / "construct.yaml").read_text(encoding="utf-8")
    assert "app/python_scripts/launch_jupyter.py: Example App/launch_jupyter.py" in construct

    post_install = (repo / "app/bash_bat_scripts/post_install.bat").read_text(encoding="utf-8")
    assert 'SET "PROJECT_ROOT=%PREFIX%\\Example App"' in post_install
    assert "import example_pkg;" in post_install
    assert "pip-system-certs" not in post_install

    generated_launcher = (repo / "app/python_scripts/launch_jupyter.py").read_text(encoding="utf-8")
    assert 'PROJECT_DISPLAY_NAME = "Example App"' in generated_launcher
    assert (repo / ".github/workflows/tests.yml").is_file()
    assert (repo / "tests/test_installer_configuration.py").is_file()
