import os
import shutil
import logging
import sys
import subprocess
import platform

logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

def request_yes_no(action: str) -> bool:
    while True:
        resp = input(f"{action}, do you want to continue? [Y/n]: ")
        if resp.lower() in ["y", "yes"]:
            return
        logger.info("Aborting installation...")
        sys.exit(1)

def fail(msg: str) -> None:
    logger.error(f"❌ {msg}")
    sys.exit(1)

def get_brew_path() -> str:
    if sys.platform == "darwin":
        return "/opt/homebrew/bin/brew" if platform.processor() == "arm" else "/usr/local/bin/brew"
    else:
        return "/home/linuxbrew/.linuxbrew/bin/brew"

def check_git():
    if shutil.which("git") is None:
        fail("Requirement missing, you must install Git before installing SWE-agent. See: https://git-scm.com/book/en/v2/Getting-Started-Installing-Git")
    logger.info("🔍 Git detected")

def check_winget():
    if shutil.which("winget") is None:
        fail("Requirement missing, you must install WinGet before installing SWE-agent. See: https://learn.microsoft.com/en-us/windows/package-manager/winget/#install-winget")
    logger.info("🔍 WinGet detected")

def install_homebrew():
    if shutil.which("brew") is not None:
        logger.info("🍺 Homebrew detected, skipping installation")
        return
    if shutil.which("curl") is None:
        fail("Requirement missing, you must install curl before installing SWE-agent. See: https://curl.se/download.html")
        return
    request_yes_no("🍺 Installing Homebrew")
    os.environ["NONINTERACTIVE"] = "1"
    brew_install = subprocess.run(["/bin/bash", "-c", "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"], capture_output=True)
    if brew_install.returncode != 0:
        fail(f"Failed to install Homebrew. Error: {brew_install.stderr}")

def install_docker_windows():
    check_winget()

    request_yes_no("🐳 Installing Docker via WinGet")
    docker_install = subprocess.run(["winget", "install", "Docker.DockerCLI"], capture_output=True)
    if docker_install.returncode != 0:
        fail(f"Failed to install Docker via WinGet. Error: {docker_install.stderr}")

def install_docker_unix():
    install_homebrew()

    request_yes_no("🐳 Installing Docker via Homebrew")
    docker_install = subprocess.run([get_brew_path(), "install", "docker"], capture_output=True)
    if docker_install.returncode != 0:
        fail(f"Failed to install Docker via Homebrew. Error: {docker_install.stderr}")

def install_docker():
    if shutil.which("docker") is not None:
        logger.info("🐳 Docker detected, skipping installation")
        return
    if sys.platform == "darwin" or sys.platform == "linux":
        install_docker_unix()
    elif sys.platform == "win32":
        install_docker_windows()
    else:
        fail(f"Unsupported platform: {sys.platform}")
def build_images():
    docker_up = subprocess.run(["docker", "info"], capture_output=True)
    if docker_up.returncode != 0:
        fail("Failed to build images as Docker is not running. Please start the daemon and retry.")

    logger.info("🔨 Building Docker images")


def main():
    check_git()
    install_docker()
    build_images()

if __name__ == "__main__":
    main()