"""
MCL build script.

Usage:
    python build.py              # Full build (clean + test + exe + release zip)
    python build.py --skip-test  # Skip unit tests
    python build.py --clean-only # Only clean build artifacts
    python build.py --dev        # Development build (no UPX, debug info)
    python build.py --no-archive # Skip local release zip creation
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SPEC_FILE = ROOT_DIR / "MCL.spec"
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
RELEASE_DIR = ROOT_DIR / "release"
EXE_NAME = "MouseControlLayer.exe"
PACKAGE_EXE_NAME = "MouseControlLayer.exe"
NATIVE_CRATE_DIR = ROOT_DIR / "rust" / "input_backend"
NATIVE_OUTPUT_DIR = ROOT_DIR / "native"
NATIVE_DLL_NAME = "mcl_input_backend.dll"
NATIVE_VERSION_NAME = "mcl_input_backend.version"
MIN_BUILD_PYTHON = (3, 9)
MAX_BUILD_PYTHON_EXCLUSIVE = (3, 15)
PREFERRED_WINDOWS_PYTHON_VERSIONS = ("3.13", "3.12", "3.11", "3.10", "3.9")
REEXEC_ENV_FLAG = "MCL_BUILD_PYTHON_REEXEC"

SOURCE_FILES = [
    "app_logging.py",
    "app_paths.py",
    "app_runtime.py",
    "i18n_manager.py",
    "mouse_center_lock_gui.py",
    "settings_manager.py",
    "win_api.py",
    "widgets.py",
    "services/action_scheduler.py",
    "services/clicker_service.py",
    "services/clicker_profile_controller.py",
    "services/input_backends.py",
    "services/input_service.py",
    "services/native_input.py",
    "services/lock_service.py",
    "services/macro_service.py",
    "services/settings_apply_controller.py",
    "services/sound_service.py",
    "services/theme_service.py",
    "services/tray_service.py",
    "ui/main_window.py",
    "ui/pages/common.py",
    "ui/pages/simple_page.py",
    "ui/pages/advanced_page.py",
    "ui/forms/clicker_profile_form.py",
    "ui/forms/settings_form.py",
    "ui/presenters/main_window_presenter.py",
    "ui/presenters/tray_presenter.py",
]


def step(name: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")


def run(cmd: list[str], *, check: bool = True, cwd: Path | None = None) -> subprocess.CompletedProcess:
    print(f"  > {' '.join(str(c) for c in cmd)}")
    return subprocess.run(cmd, check=check, cwd=cwd or ROOT_DIR)


def _version_tuple_text(version: tuple[int, int, int]) -> str:
    return ".".join(str(part) for part in version)


def _is_supported_build_python(version_info: tuple[int, int, int]) -> bool:
    return MIN_BUILD_PYTHON <= version_info[:2] < MAX_BUILD_PYTHON_EXCLUSIVE


def _candidate_python_commands() -> list[list[str]]:
    commands: list[list[str]] = []

    env_python = os.environ.get("MCL_BUILD_PYTHON")
    if env_python:
        commands.append([env_python])

    commands.append([sys.executable])
    if os.name == "nt":
        commands.append(["python"])
        commands.extend([["py", f"-{version}"] for version in PREFERRED_WINDOWS_PYTHON_VERSIONS])
    else:
        commands.extend([[f"python{version}"] for version in PREFERRED_WINDOWS_PYTHON_VERSIONS])
        commands.extend([["python3"], ["python"]])

    deduped: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for command in commands:
        key = tuple(command)
        if key not in seen:
            deduped.append(command)
            seen.add(key)
    return deduped


def _probe_python(command: list[str]) -> tuple[tuple[int, int, int], str, bool] | None:
    probe = (
        "import importlib.util, sys\n"
        "print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')\n"
        "print(sys.executable)\n"
        "print('1' if importlib.util.find_spec('PyInstaller') is not None else '0')\n"
    )
    try:
        result = subprocess.run(
            [*command, "-c", probe],
            check=False,
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(lines) < 3:
        return None
    try:
        parts = tuple(int(part) for part in lines[0].split(".")[:3])
    except ValueError:
        return None
    if len(parts) != 3:
        return None
    return parts, lines[1], lines[2] == "1"


def _same_executable(left: str, right: str) -> bool:
    try:
        return Path(left).resolve() == Path(right).resolve()
    except OSError:
        return left.lower() == right.lower()


def _current_python_has_pyinstaller() -> bool:
    return importlib.util.find_spec("PyInstaller") is not None


def ensure_build_python() -> int | None:
    current_version = sys.version_info[:3]
    current_supported = _is_supported_build_python(current_version)
    current_ready = current_supported and _current_python_has_pyinstaller()
    if current_ready:
        print(f"Build Python: {sys.version.split()[0]} ({sys.executable})")
        return None

    print("Selecting build Python runtime")
    print(f"  Current: {sys.version.split()[0]} ({sys.executable})")
    if not current_supported:
        print(
            "  Reason: packaging supports Python "
            f"{_version_tuple_text((*MIN_BUILD_PYTHON, 0)[:3])}+ "
            f"and < {_version_tuple_text((*MAX_BUILD_PYTHON_EXCLUSIVE, 0)[:3])}; "
            f"{sys.version.split()[0]} is not suitable."
        )
    elif not _current_python_has_pyinstaller():
        print("  Reason: PyInstaller is not installed in the current runtime.")

    for command in _candidate_python_commands():
        probed = _probe_python(command)
        if probed is None:
            continue
        version, executable, has_pyinstaller = probed
        if not _is_supported_build_python(version):
            print(f"  Skip {executable}: Python {_version_tuple_text(version)} is outside build range.")
            continue
        if not has_pyinstaller:
            print(f"  Skip {executable}: PyInstaller not installed.")
            continue
        if _same_executable(executable, sys.executable):
            print(f"  Selected current runtime: Python {_version_tuple_text(version)}")
            return None

        if os.environ.get(REEXEC_ENV_FLAG) == "1":
            print(f"  FAIL: re-exec guard tripped before switching to {executable}.")
            return 1

        print(f"  Selected: Python {_version_tuple_text(version)} ({executable})")
        env = os.environ.copy()
        env[REEXEC_ENV_FLAG] = "1"
        result = subprocess.run([*command, str(Path(__file__).resolve()), *sys.argv[1:]], cwd=ROOT_DIR, env=env)
        return result.returncode

    print("  FAIL: no suitable Python runtime with PyInstaller was found.")
    print("        Preferred local default for packaging: Python 3.13, fallback: Python 3.12.")
    return 1


def clean() -> None:
    step("Cleaning build artifacts")
    for d in [DIST_DIR, BUILD_DIR, RELEASE_DIR]:
        if d.exists():
            shutil.rmtree(d)
            print(f"  Removed {d}")
    for item in ROOT_DIR.iterdir():
        if item.is_dir() and item.name.startswith("build_"):
            shutil.rmtree(item)
            print(f"  Removed {item}")
        if item.is_dir() and item.name.startswith("dist_"):
            shutil.rmtree(item)
            print(f"  Removed {item}")
    print("  Clean complete.")


def syntax_check() -> bool:
    step("Syntax check (AST parse)")
    ok = True
    for rel_path in SOURCE_FILES:
        full = ROOT_DIR / rel_path
        if not full.exists():
            print(f"  SKIP {rel_path} (not found)")
            continue
        try:
            ast.parse(full.read_text(encoding="utf-8"), filename=rel_path)
            print(f"  AST_OK {rel_path}")
        except SyntaxError as e:
            print(f"  FAIL  {rel_path}: {e}")
            ok = False
    return ok


def validate_json_assets() -> bool:
    step("Validating JSON assets")
    ok = True
    roots = [ROOT_DIR / "i18n", ROOT_DIR / "examples" / "mouse-macros"]
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            rel_path = path.relative_to(ROOT_DIR)
            try:
                import json

                json.loads(path.read_text(encoding="utf-8"))
                print(f"  JSON_OK {rel_path}")
            except Exception as exc:
                print(f"  FAIL    {rel_path}: {exc}")
                ok = False
    return ok


def run_tests() -> bool:
    step("Running unit tests")
    result = run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        check=False,
    )
    if result.returncode != 0:
        print("  Tests FAILED.")
        return False
    print("  All tests passed.")
    return True


def build_native_input_backend() -> bool:
    step("Building Rust input backend")
    if os.name != "nt":
        print("  SKIP: native input backend is Windows-only.")
        return True
    if not (NATIVE_CRATE_DIR / "Cargo.toml").exists():
        print(f"  SKIP: Rust crate not found: {NATIVE_CRATE_DIR}")
        return True
    if shutil.which("cargo") is None:
        print("  FAIL: cargo not found; install Rust or provide native/mcl_input_backend.dll.")
        return False

    result = run(["cargo", "build", "--release"], check=False, cwd=NATIVE_CRATE_DIR)
    if result.returncode != 0:
        existing_dll = NATIVE_OUTPUT_DIR / NATIVE_DLL_NAME
        if existing_dll.exists():
            print(f"  WARN: Rust backend build failed; keeping existing {existing_dll}.")
            return True
        print("  WARN: Rust backend build failed; continuing with Python SendInput fallback.")
        print("        Install Visual Studio Build Tools (C++ workload) to produce native/mcl_input_backend.dll.")
        return True

    built_dll = NATIVE_CRATE_DIR / "target" / "release" / NATIVE_DLL_NAME
    if not built_dll.exists():
        print(f"  FAIL: expected DLL not found: {built_dll}")
        return False

    NATIVE_OUTPUT_DIR.mkdir(exist_ok=True)
    target_dll = NATIVE_OUTPUT_DIR / NATIVE_DLL_NAME
    try:
        shutil.copy2(built_dll, target_dll)
    except PermissionError as exc:
        if target_dll.exists():
            print(f"  WARN: {target_dll} is locked by a running process; keeping existing DLL. ({exc})")
        else:
            print(f"  FAIL: cannot write {target_dll}: {exc}")
            return False
    (NATIVE_OUTPUT_DIR / NATIVE_VERSION_NAME).write_text(
        "name=mcl_input_backend\nversion=0.1.0\narch=x86_64\nprofile=release\n",
        encoding="utf-8",
    )
    print(f"  OK: {target_dll}")
    return True


def extract_version() -> str:
    readme = ROOT_DIR / "README.md"
    if readme.exists():
        for line in readme.read_text(encoding="utf-8").splitlines():
            if line.startswith("### v"):
                return line.strip().lstrip("# ").strip()
    return datetime.now().strftime("%Y.%m.%d")


def build_exe(*, dev: bool = False) -> bool:
    step("Building executable with PyInstaller")
    if not SPEC_FILE.exists():
        print(f"  ERROR: Spec file not found: {SPEC_FILE}")
        return False

    if sys.version_info >= (3, 15):
        print(f"  FAIL: PyInstaller does not support this Python runtime yet: {sys.version.split()[0]}")
        print("        Use Python 3.12/3.13 for local packaging, or run the GitHub Actions release workflow.")
        return False

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
    ]
    if dev:
        cmd.append("--debug")
    cmd.append(str(SPEC_FILE))

    result = run(cmd, check=False)
    if result.returncode != 0:
        print("  Build FAILED.")
        return False

    exe_path = DIST_DIR / EXE_NAME
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"  Build SUCCESS: {exe_path} ({size_mb:.1f} MB)")
        return True

    print(f"  ERROR: Expected output not found: {exe_path}")
    return False


def verify_build() -> bool:
    step("Verifying build output")
    exe_path = DIST_DIR / EXE_NAME
    if not exe_path.exists():
        print(f"  FAIL: {exe_path} does not exist.")
        return False
    size_mb = exe_path.stat().st_size / (1024 * 1024)
    if size_mb < 1:
        print(f"  FAIL: Executable seems too small ({size_mb:.1f} MB).")
        return False
    print(f"  OK: {exe_path} ({size_mb:.1f} MB)")
    return True


def _safe_archive_tag(version: str) -> str:
    value = version.strip() or datetime.now().strftime("%Y.%m.%d")
    value = re.sub(r"[^0-9A-Za-z._-]+", "-", value).strip("-")
    return value or datetime.now().strftime("%Y.%m.%d")


def prepare_release_archive(version: str) -> bool:
    step("Preparing local release archive")
    exe_path = DIST_DIR / EXE_NAME
    if not exe_path.exists():
        print(f"  FAIL: build output not found: {exe_path}")
        return False

    RELEASE_DIR.mkdir(exist_ok=True)
    package_exe = RELEASE_DIR / PACKAGE_EXE_NAME
    if package_exe.exists():
        package_exe.unlink()
    shutil.copy2(exe_path, package_exe)

    tag = _safe_archive_tag(version)
    zip_path = RELEASE_DIR / f"MCL-{tag}-windows-x64.zip"
    checksum_path = Path(f"{zip_path}.sha256")
    for path in [zip_path, checksum_path]:
        if path.exists():
            path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(package_exe, arcname=PACKAGE_EXE_NAME)
    package_exe.unlink()

    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest().upper()
    checksum_path.write_text(f"{digest}  {zip_path.name}\n", encoding="ascii")
    print(f"  OK: {zip_path}")
    print(f"  OK: {checksum_path}")
    print(f"  Archive entry: {PACKAGE_EXE_NAME}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="MCL build script")
    parser.add_argument("--skip-test", action="store_true", help="Skip unit tests")
    parser.add_argument("--clean-only", action="store_true", help="Only clean build artifacts")
    parser.add_argument("--dev", action="store_true", help="Development build (debug info, no UPX)")
    parser.add_argument("--no-clean", action="store_true", help="Skip cleaning before build")
    parser.add_argument("--no-archive", action="store_true", help="Skip local release zip creation")
    args = parser.parse_args()

    if not args.clean_only:
        selected_python_result = ensure_build_python()
        if selected_python_result is not None:
            return selected_python_result

    version = extract_version()
    print(f"MCL Build Script - version {version}")

    if args.clean_only:
        clean()
        return 0

    if not args.no_clean:
        clean()

    if not syntax_check():
        return 1

    if not validate_json_assets():
        return 1

    if not args.skip_test:
        if not run_tests():
            return 1
    else:
        step("Skipping unit tests (--skip-test)")

    if not build_native_input_backend():
        return 1

    if not build_exe(dev=args.dev):
        return 1

    if not verify_build():
        return 1

    if not args.no_archive:
        if not prepare_release_archive(version):
            return 1

    step("Build complete")
    print(f"  Output: {DIST_DIR / EXE_NAME}")
    if not args.no_archive:
        print(f"  Package: {RELEASE_DIR / f'MCL-{_safe_archive_tag(version)}-windows-x64.zip'}")
    print(f"  Version: {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
