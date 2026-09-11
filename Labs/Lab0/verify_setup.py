"""
ME416 Lab 1 Prelab Verification Script
"""

import importlib
import platform
import datetime
import hashlib
import shutil
import subprocess

REQUIRED_PACKAGES = ["lerobot", "mujoco", "matplotlib", "ipywidgets"]

REQUIRED_VSCODE_EXTENSIONS = {
    "ms-python.python": "Python",
    "ms-toolsai.jupyter": "Jupyter",
    "ms-python.vscode-pylance": "Pylance",
    #"github.copilot": "GitHub Copilot",
}

IS_WINDOWS = platform.system() == "Windows"


def run_code_command(args):
    code_path = shutil.which("code")
    cmd = [code_path] + args
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=15, shell=IS_WINDOWS
    )


def check_packages(missing):
    for pkg in REQUIRED_PACKAGES:
        try:
            mod = importlib.import_module(pkg)
            version = getattr(mod, "__version__", "unknown")
            print(f"[OK] {pkg} (version: {version})")
        except ImportError:
            print(f"[MISSING] {pkg}")
            missing.append(pkg)


def check_vscode(missing):
    code_path = shutil.which("code")
    if not code_path:
        print(
            "[MISSING] VS Code ('code' command not found on PATH — on macOS, "
            "open the Command Palette (Cmd+Shift+P) and run "
            "'Shell Command: Install \\'code\\' command in PATH', then try again)"
        )
        missing.append("VS Code")
        return

    try:
        result = run_code_command(["--version"])
        lines = result.stdout.strip().splitlines()
        version = lines[0] if lines else "unknown"
        print(f"[OK] VS Code (version: {version})")
    except Exception as e:
        print(f"[OK] VS Code (version: unknown — {e})")

    try:
        result = run_code_command(["--list-extensions"])
        installed = set(e.strip().lower() for e in result.stdout.splitlines() if e.strip())
    except Exception as e:
        print(f"[MISSING] Could not list VS Code extensions ({e})")
        missing.extend(REQUIRED_VSCODE_EXTENSIONS.values())
        return

    if not installed:
        print("[MISSING] 'code --list-extensions' returned no output — check VS Code is on PATH")
        missing.extend(REQUIRED_VSCODE_EXTENSIONS.values())
        return

    for ext_id, name in REQUIRED_VSCODE_EXTENSIONS.items():
        if ext_id.lower() in installed:
            print(f"[OK] VS Code extension: {name}")
        else:
            print(f"[MISSING] VS Code extension: {name}")
            missing.append(name)


def main():
    print("=== ME416 Lab 1 Prelab Verification ===")
    print(f"Python version: {platform.python_version()}")
    print()

    missing = []
    check_packages(missing)
    print()
    check_vscode(missing)
    print()

    name = input("Enter your full name: ").strip()
    timestamp = datetime.datetime.now().isoformat()
    status = "PASS" if not missing else "FAIL"
    code_input = f"{name}|{status}|{timestamp}"
    confirmation_code = hashlib.sha256(code_input.encode()).hexdigest()[:12]

    print()
    print(f"Status: {status}")
    if missing:
        print(f"Missing items: {', '.join(missing)}")
    print(f"Confirmation code: {confirmation_code}")
    print("Copy this entire output and paste it into the Lab 1 Prelab submission on Canvas.")


if __name__ == "__main__":
    main()