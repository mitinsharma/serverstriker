# 🚀 ServerStriker

**ServerStriker** is a lightweight, self-hosted Linux server monitoring agent that continuously tracks system health and sends alerts via **webhooks** (n8n, Slack, Discord, Microsoft Teams, custom APIs).

It is designed to be **simple to install**, **low on resources**, and **easy to extend**, making it ideal for VPS, cloud servers, and self-hosted infrastructure.

---

## 📘 Documentation

👉 **New users should start here:**  
**[🧭 Step-by-Step Installation & Usage Guide](#-step-by-step-installation--usage-guide)**

This guide walks you through installing, configuring, running, and managing ServerStriker on an Ubuntu server.

---

## ✨ Features

- 🔥 CPU usage monitoring  
- 🚨 RAM usage monitoring  
- ⚠️ Disk space monitoring  
- 🔧 System service health checks (nginx, mysql, docker, etc.)  
- 🔴 Detection of failed systemd services  
- 🚨 Security alerts for failed SSH login attempts  
- 📦 Daily check for pending system updates  
- 📡 Webhook-based notifications (vendor-agnostic)  
- ♻️ Runs as a systemd service (auto-restart, runs on boot)  
- ⚡ Minimal dependencies & low overhead  

---

## 📡 Webhook-First Design

ServerStriker sends alerts as **JSON payloads** to a webhook endpoint, making it compatible with:

- n8n  
- Slack (via workflows)  
- Discord  
- Microsoft Teams  
- PagerDuty  
- Zapier  
- Custom APIs  

No third-party lock-in.

### Example Webhook Payload

```json
{
  "server": "prod-server-1",
  "timestamp": "2025-01-01T12:00:00Z",
  "message": "🔥 High CPU Usage: 92%"
}


