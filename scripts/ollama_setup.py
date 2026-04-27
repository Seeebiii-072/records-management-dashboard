"""
ollama_setup.py - Ollama Auto Installer + Model Puller
=======================================================
Automatically:
1. Detects if Ollama is installed
2. Downloads & installs Ollama (Windows/Mac/Linux)
3. Starts Ollama server
4. Pulls llama3 model
5. Returns ready status
"""

import os
import sys
import subprocess
import platform
import time
import urllib.request
import urllib.error
import json


OLLAMA_MODEL = "tinyllama"
OLLAMA_API  = "http://localhost:11434"


# ─── CHECK ────────────────────────────────────────────────────────────────────

def is_ollama_installed():
    """Ollama install hai ya nahi check karo."""
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def is_ollama_running():
    """Ollama server chal raha hai ya nahi."""
    try:
        req = urllib.request.urlopen(f"{OLLAMA_API}/api/tags", timeout=3)
        return req.status == 200
    except Exception:
        return False


def is_model_available():
    """llama3 model available hai ya nahi."""
    try:
        req = urllib.request.urlopen(f"{OLLAMA_API}/api/tags", timeout=5)
        data = json.loads(req.read())
        models = [m["name"] for m in data.get("models", [])]
        return any(OLLAMA_MODEL in m for m in models)
    except Exception:
        return False


# ─── INSTALL ──────────────────────────────────────────────────────────────────

def install_ollama_windows(status_callback=None):
    """Windows pe Ollama install karo."""
    msg = "📥 Downloading Ollama for Windows..."
    print(msg)
    if status_callback:
        status_callback(msg)

    url      = "https://ollama.com/download/OllamaSetup.exe"
    installer = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "OllamaSetup.exe")

    try:
        urllib.request.urlretrieve(url, installer)
        msg = "⚙️ Installing Ollama (silent install)..."
        print(msg)
        if status_callback:
            status_callback(msg)

        subprocess.run([installer, "/S"], check=True, timeout=120)

        # PATH refresh
        os.environ["PATH"] += r";C:\Users\{}\AppData\Local\Programs\Ollama".format(
            os.environ.get("USERNAME", "")
        )

        msg = "✅ Ollama installed!"
        print(msg)
        if status_callback:
            status_callback(msg)
        return True

    except Exception as e:
        print(f"❌ Install failed: {e}")
        if status_callback:
            status_callback(f"❌ Install failed: {e}")
        return False


def install_ollama_mac_linux(status_callback=None):
    """Mac/Linux pe Ollama install karo."""
    msg = "📥 Installing Ollama via curl..."
    print(msg)
    if status_callback:
        status_callback(msg)

    try:
        result = subprocess.run(
            "curl -fsSL https://ollama.com/install.sh | sh",
            shell=True, check=True, timeout=180,
            capture_output=True, text=True
        )
        msg = "✅ Ollama installed!"
        print(msg)
        if status_callback:
            status_callback(msg)
        return True
    except Exception as e:
        print(f"❌ Install failed: {e}")
        if status_callback:
            status_callback(f"❌ Install failed: {e}")
        return False


def install_ollama(status_callback=None):
    """OS detect karke Ollama install karo."""
    system = platform.system()
    if system == "Windows":
        return install_ollama_windows(status_callback)
    else:
        return install_ollama_mac_linux(status_callback)


# ─── START SERVER ─────────────────────────────────────────────────────────────

def start_ollama_server(status_callback=None):
    """Ollama server start karo background mein."""
    if is_ollama_running():
        return True

    msg = "🚀 Starting Ollama server..."
    print(msg)
    if status_callback:
        status_callback(msg)

    try:
        if platform.system() == "Windows":
            subprocess.Popen(
                ["ollama", "serve"],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

        # Wait for server
        for i in range(15):
            time.sleep(2)
            if is_ollama_running():
                msg = "✅ Ollama server is running!"
                print(msg)
                if status_callback:
                    status_callback(msg)
                return True

        return is_ollama_running()

    except Exception as e:
        print(f"❌ Server start failed: {e}")
        return False


# ─── PULL MODEL ───────────────────────────────────────────────────────────────

def pull_model(status_callback=None):
    """llama3 model download karo."""
    if is_model_available():
        msg = f"✅ {OLLAMA_MODEL} already available!"
        print(msg)
        if status_callback:
            status_callback(msg)
        return True

    msg = f"📥 Downloading {OLLAMA_MODEL} model (this may take 5-10 mins on first run)..."
    print(msg)
    if status_callback:
        status_callback(msg)

    try:
        process = subprocess.Popen(
            ["ollama", "pull", OLLAMA_MODEL],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in process.stdout:
            line = line.strip()
            if line:
                print(f"   {line}")
                if status_callback and ("pulling" in line.lower() or
                                        "%" in line or
                                        "success" in line.lower()):
                    status_callback(f"📥 {line}")

        process.wait()
        success = process.returncode == 0
        if success:
            msg = f"✅ {OLLAMA_MODEL} model ready!"
            print(msg)
            if status_callback:
                status_callback(msg)
        return success

    except Exception as e:
        print(f"❌ Model pull failed: {e}")
        if status_callback:
            status_callback(f"❌ Model pull failed: {e}")
        return False


# ─── MAIN SETUP ───────────────────────────────────────────────────────────────

def setup_ollama(status_callback=None):
    """
    Full Ollama setup pipeline:
    1. Check installed
    2. Install if needed
    3. Start server
    4. Pull model
    Returns: (success: bool, message: str)
    """
    print("\n" + "="*50)
    print("  OLLAMA SETUP PIPELINE")
    print("="*50)

    # Step 1: Install check
    if not is_ollama_installed():
        msg = "⚠️ Ollama not found. Installing automatically..."
        print(msg)
        if status_callback:
            status_callback(msg)

        installed = install_ollama(status_callback)
        if not installed:
            return False, "❌ Ollama installation failed. Please install manually from https://ollama.com"
    else:
        msg = "✅ Ollama is already installed"
        print(msg)
        if status_callback:
            status_callback(msg)

    # Step 2: Start server
    if not start_ollama_server(status_callback):
        return False, "❌ Could not start Ollama server"

    # Step 3: Pull model
    if not pull_model(status_callback):
        return False, f"❌ Could not download {OLLAMA_MODEL} model"

    return True, f"✅ Ollama + {OLLAMA_MODEL} ready!"
