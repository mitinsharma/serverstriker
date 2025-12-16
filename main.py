#!/usr/bin/env python3
import time
import psutil
import os
import argparse
import requests
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import json

# -----------------------------
# ServerStriker
# -----------------------------
VERSION = "3.9"
CHECK_INTERVAL = 300  # seconds

LOG_FILE = "/var/log/serverstriker.log"
STATE_FILE = "/etc/serverstriker/serverstriker_state.txt"
CONFIG_FILE = "/etc/serverstriker/sst_config.json"


# -----------------------------
# Helpers
# -----------------------------
def ensure_dirs():
    """Ensure required directories exist."""
    Path("/etc/serverstriker").mkdir(parents=True, exist_ok=True)
    # Ensure log file exists (may require root)
    try:
        Path(LOG_FILE).touch(exist_ok=True)
    except PermissionError:
        # If not root, just skip creating log now
        pass
    Path(STATE_FILE).touch(exist_ok=True)


def log_message(message: str):
    """Write a message to the log file with a timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_entry)
    except PermissionError:
        # fallback to stdout if not allowed (install should run as root anyway)
        print(log_entry, end="")


def load_config():
    """Load config from file if available."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as file:
                return json.load(file)
    except Exception as e:
        log_message(f"Error loading config: {e}")
    return None


def save_config(config: dict):
    """Save config dict to CONFIG_FILE."""
    ensure_dirs()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


def read_last_position() -> int:
    """Read last log position from state file"""
    try:
        with open(STATE_FILE, "r") as f:
            return int(f.read().strip() or "0")
    except (FileNotFoundError, ValueError):
        return 0


def save_last_position(position: int):
    """Save last log position to state file"""
    ensure_dirs()
    with open(STATE_FILE, "w") as f:
        f.write(str(position))


# -----------------------------
# Webhook Notifications
# -----------------------------
def send_webhook(message: str):
    """
    Send message to webhook.
    Payload is JSON so it works with n8n/Slack/Discord/etc (via their webhook adapters).
    """
    config = load_config()
    if not config:
        print("Please run 'ServerStriker -init' to initialize.")
        log_message("Config missing. Please run ServerStriker -init")
        return

    server_name = config.get("server_name", "Unknown Server")
    webhook_url = config.get("webhook_url", "").strip()

    if not webhook_url:
        print("Webhook not set. Run: ServerStriker -setwebhook")
        log_message("Webhook URL not set. Run ServerStriker -setwebhook")
        return

    payload = {
        "server": server_name,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message": message
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        log_message(f"Webhook error: {e}")


# -----------------------------
# Checks
# -----------------------------
def check_cpu_usage(show=False):
    usage = psutil.cpu_percent(interval=1)
    if usage > 80 or show:
        return [f"🔥 High CPU Usage: {usage}%"]
    return []


def check_memory_usage(show=False):
    usage = psutil.virtual_memory().percent
    if usage > 80 or show:
        return [f"🚨 High RAM Usage: {usage}%"]
    return []


def check_disk_usage(show=False):
    usage = psutil.disk_usage("/").percent
    if usage > 80 or show:
        return [f"⚠️ Low Disk Space: {usage}% used"]
    return []


def _split_services(services_str: str):
    if not services_str:
        return []
    # supports "nginx,mysql" or "nginx, mysql"
    return [s.strip() for s in services_str.split(",") if s.strip()]


def check_running_services(show=False):
    config = load_config()
    if not config:
        return []

    services_str = config.get("services", "")
    services = _split_services(services_str)

    messages = []
    for service in services:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True,
                text=True
            )
            if result.stdout.strip() != "active":
                messages.append(f"❌ {service} is down!")
            elif show:
                messages.append(f"✔️ {service} is up!")
        except Exception as e:
            log_message(f"Error checking service {service}: {e}")
    return messages


def check_security_logs():
    try:
        logins = subprocess.run(
            ["grep", "Failed password", "/var/log/auth.log"],
            capture_output=True,
            text=True
        )
        return len(logins.stdout.splitlines())
    except Exception as e:
        log_message(f"Error reading auth.log: {e}")
        return 0


def clear_ssh_attempts(log_file="/var/log/auth.log"):
    """
    WARNING: This modifies auth.log (requires root).
    Kept because your original code does it, but use carefully.
    """
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
        filtered_lines = [line for line in lines if "sshd" not in line]
        with open(log_file, "w") as f:
            f.writelines(filtered_lines)
        log_message(f"SSH attempts cleared from {log_file}.")
    except PermissionError:
        log_message("Permission denied. Need root to modify auth.log.")
    except FileNotFoundError:
        log_message(f"Log file not found: {log_file}")
    except Exception as e:
        log_message(f"An error occurred clearing ssh attempts: {e}")


def check_system_errors():
    """
    Check ServerStriker log for new critical lines.
    Uses STATE_FILE to only send new errors.
    """
    messages = []
    try:
        file_size = os.path.getsize(LOG_FILE)
        last_position = read_last_position()

        if file_size < last_position:
            last_position = 0  # rotated

        with open(LOG_FILE, "r") as f:
            f.seek(last_position)
            for line in f:
                low = line.lower()
                if "error" in low or "critical" in low or "failed" in low:
                    messages.append(f"🚨 System Error: {line.strip()}")
            save_last_position(f.tell())
    except Exception as e:
        log_message(f"Error checking system logs: {e}")
    return messages


def check_pending_updates():
    try:
        result = subprocess.check_output(["apt", "list", "--upgradable"], text=True)
        updates = [line.split("/")[0] for line in result.splitlines() if "/" in line]
        if updates:
            return [f"📦 {len(updates)} packages can be upgraded."]
    except Exception as e:
        log_message(f"Error checking updates: {e}")
    return []


def check_services_status():
    messages = []
    try:
        result = subprocess.check_output(
            ["systemctl", "list-units", "--type=service", "--state=failed", "--no-pager"],
            text=True
        )
        lines = result.splitlines()
        failed = []
        for line in lines:
            # crude filter: "something.service loaded failed failed ..."
            if ".service" in line and "failed" in line:
                parts = line.split()
                if parts:
                    failed.append(parts[0])
        if failed:
            messages.append(f"🔴 Failed Services: {', '.join(failed)}")
    except Exception as e:
        log_message(f"Error checking failed services: {e}")
    return messages


# -----------------------------
# Background Loop (systemd runs this)
# -----------------------------
def run_daemon():
    ensure_dirs()
    log_message("ServerStriker daemon started.")

    last_daily_check = datetime.now() - timedelta(days=1)

    while True:
        all_messages = []

        # Frequent checks
        all_messages.extend(check_cpu_usage())
        all_messages.extend(check_memory_usage())
        all_messages.extend(check_disk_usage())
        all_messages.extend(check_running_services())

        # Daily checks
        if datetime.now() - last_daily_check >= timedelta(days=1):
            all_messages.extend(check_cpu_usage(True))
            all_messages.extend(check_memory_usage(True))
            all_messages.extend(check_disk_usage(True))
            all_messages.extend(check_running_services(True))

            failed_logins = check_security_logs()
            if failed_logins > 5:
                all_messages.append(f"🚨 Security Alert: {failed_logins} failed SSH logins detected!")
                clear_ssh_attempts()

            all_messages.extend(check_system_errors())
            all_messages.extend(check_pending_updates())
            all_messages.extend(check_services_status())

            last_daily_check = datetime.now()

        if all_messages:
            send_webhook("\n".join(all_messages))

        time.sleep(CHECK_INTERVAL)


# -----------------------------
# CLI commands
# -----------------------------
def init_config():
    ensure_dirs()

    config = load_config() or {}
    config["server_name"] = input("Enter server name: ").strip()
    config["webhook_url"] = input("Enter webhook URL (can be blank for now): ").strip()
    config["services"] = input("Enter service names to check (ex: nginx,mysql): ").strip()

    save_config(config)
    print("\n✅ ServerStriker initialized.\n")
    print("Next steps:")
    print("  1) (optional) ServerStriker -setwebhook")
    print("  2) sudo systemctl start serverstriker")
    print("  3) sudo systemctl status serverstriker\n")


def set_webhook():
    config = load_config() or {}
    webhook = input("Enter webhook URL: ").strip()
    config["webhook_url"] = webhook
    save_config(config)
    print("✅ Webhook saved successfully.")


def add_service():
    config = load_config() or {}
    current = config.get("services", "")
    new_service = input("Enter service name to add (ex: nginx): ").strip()

    services = set(_split_services(current))
    if new_service:
        services.add(new_service)

    config["services"] = ",".join(sorted(services))
    save_config(config)
    print(f"✅ Services updated: {config['services']}")


def show_config():
    cfg = load_config()
    if not cfg:
        print("No config found. Run: ServerStriker -init")
        return
    # do not print anything "secret-like" (webhook could be sensitive)
    safe = dict(cfg)
    if safe.get("webhook_url"):
        safe["webhook_url"] = safe["webhook_url"][:35] + "..."  # partial
    print(json.dumps(safe, indent=4))


def status_service():
    try:
        out = subprocess.check_output(["systemctl", "is-active", "serverstriker"], text=True).strip()
        if out == "active":
            print("ServerStriker is running (systemd: active).")
        else:
            print(f"ServerStriker status: {out}")
    except Exception as e:
        print("Could not read systemd status. Try: sudo systemctl status serverstriker")
        log_message(f"Status check failed: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="ServerStriker - server monitoring agent with webhook alerts."
    )
    parser.add_argument("-version", action="store_true", help="Print version")
    parser.add_argument("-init", action="store_true", help="Initialize config")
    parser.add_argument("-setwebhook", action="store_true", help="Set or update webhook URL")
    parser.add_argument("-addservice", action="store_true", help="Add a service to monitor")
    parser.add_argument("-config", action="store_true", help="Show current config (safe output)")
    parser.add_argument("-status", action="store_true", help="Show systemd service status")
    parser.add_argument("-run", action="store_true", help=argparse.SUPPRESS)  # internal for systemd

    args = parser.parse_args()

    if args.version:
        print(f"ServerStriker Version: {VERSION}")
        return

    if args.init:
        init_config()
        return

    if args.setwebhook:
        set_webhook()
        return

    if args.addservice:
        add_service()
        return

    if args.config:
        show_config()
        return

    if args.status:
        status_service()
        return

    if args.run:
        run_daemon()
        return

    parser.print_help()


if __name__ == "__main__":
    main()
