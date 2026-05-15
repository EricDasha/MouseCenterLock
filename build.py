"""
MouseCenterLock build script.

Usage:
    python build.py              # Full build (clean + test + package)
    python build.py --skip-test  # Skip unit tests
    python build.py --clean-only # Only clean build artifacts
    python build.py --dev        # Development build (no UPX, debug info)
"""
from __future__ import annotations

import argparse
import ast
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SPEC_FILE = ROOT_DIR / "MouseCenterLock.spec"
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
EXE_NAME = "MouseCenterLock.exe"

SOURCE_FILES = [
    "app_logging.py",
    "app_paths.py",
    "app_runtime.py",
    "i18n_manager.py",
    "mouse_center_lock_gui.py",
    "settings_manager.py",
    "win_api.py",
    "widgets.py",
    "services/clicker_service.py",
    "services/clicker_profile_controller.py",
    "services/lock_service.py",
    "services/settings_apply_controller.py",
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


def clean() -> None:
    step("Cleaning build artifacts")
    for d in [DIST_DIR, BUILD_DIR]:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="MouseCenterLock build script")
    parser.add_argument("--skip-test", action="store_true", help="Skip unit tests")
    parser.add_argument("--clean-only", action="store_true", help="Only clean build artifacts")
    parser.add_argument("--dev", action="store_true", help="Development build (debug info, no UPX)")
    parser.add_argument("--no-clean", action="store_true", help="Skip cleaning before build")
    args = parser.parse_args()

    version = extract_version()
    print(f"MouseCenterLock Build Script — version {version}")

    if args.clean_only:
        clean()
        return 0

    if not args.no_clean:
        clean()

    if not syntax_check():
        return 1

    if not args.skip_test:
        if not run_tests():
            return 1
    else:
        step("Skipping unit tests (--skip-test)")

    if not build_exe(dev=args.dev):
        return 1

    if not verify_build():
        return 1

    step("Build complete")
    print(f"  Output: {DIST_DIR / EXE_NAME}")
    print(f"  Version: {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
