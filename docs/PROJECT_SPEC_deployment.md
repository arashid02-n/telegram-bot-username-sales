# PROJECT_SPEC_deployment.md

## 1. Core Purpose

This document defines the deployment architecture, production environment, update workflow, and operational procedures for the BuyTelegramBots platform.

It serves as the reference for deploying, updating, debugging, and maintaining the production server.

---

## 2. Production Environment

### Server

- Ubuntu 24.04 LTS
- Hetzner VPS
- Root access
- SSH deployment

### Reverse Proxy

- Nginx
- HTTPS via Let's Encrypt (Certbot)

### Runtime

Python 3.12

Virtual Environment

```
/opt/buytelegrambots-web/web/.venv
```

Docker & Docker Compose

Systemd Services

---

## 3. Repository Layout

```
/opt/buytelegrambots-web

├── bot/
├── web/
├── docs/
├── README.md
├── PROJECT_SPEC.md
```

Git Branches

```
main
develop
feature/web
feature/bot
feature/devops
release/*
hotfix/*
```

Production always tracks:

```
origin/main
```

---

## 4. Production Services

### Website

Application

FastAPI

Runs via

```
systemd
```

Service

```
buytelegrambots-web.service
```

Port

```
127.0.0.1:8004
```

Nginx Proxy

```
443
        ↓
127.0.0.1:8004
```

---

### Docker

Docker is used only where required by the web project.

Container

```
buytelegrambots-web
```

Docker Compose location

```
/opt/buytelegrambots-web/web
```

---

## 5. Deployment Workflow

Production deployment always follows:

### Step 1

Update local repository

```
cd /opt/buytelegrambots-web

git checkout main
git fetch origin
git reset --hard origin/main
```

---

### Step 2

Determine what changed.

If only:

- Python
- HTML
- CSS
- Templates
- JSON
- Static assets

Restart the application:

```
systemctl restart buytelegrambots-web
```

---

If Docker-related files changed:

- Dockerfile
- docker-compose.yml
- requirements.txt

Rebuild:

```
cd web

docker compose down
docker compose build --no-cache
docker compose up -d

systemctl restart buytelegrambots-web
```

---

## 6. Service Verification

Check service

```
systemctl status buytelegrambots-web
```

Check logs

```
journalctl -u buytelegrambots-web -n 100
```

Check container

```
docker ps
```

Check nginx

```
nginx -t
```

---

## 7. Deployment Rules

Never edit files directly on production unless performing emergency debugging.

Production must always mirror:

```
origin/main
```

All code changes must go through:

```
feature/*
        ↓
develop
        ↓
release/*
        ↓
main
```

---

## 8. File Responsibilities

bots.json

Purpose

Homepage inventory cards.

Changing this file updates:

- homepage descriptions
- homepage cards

Requires:

```
systemctl restart buytelegrambots-web
```

---

bots_individual_pages.json

Purpose

Individual SEO landing pages.

Changing this file updates:

```
/flightticketbot
/tradegramsbot
...
```

Requires

```
systemctl restart buytelegrambots-web
```

---

Templates

```
templates/
```

Changing template files updates page layout.

Requires

```
systemctl restart buytelegrambots-web
```

---

Static Assets

```
styles.css
script.js
favicon.png
```

Restart service after modification.

---

## 9. Troubleshooting Checklist

If changes are not visible:

1. Verify repository

```
git log -1
```

2. Verify file contains expected changes

```
cat
grep
```

3. Restart service

```
systemctl restart buytelegrambots-web
```

4. Verify service

```
systemctl status buytelegrambots-web
```

5. Verify browser cache

Hard refresh

```
Ctrl + Shift + R
```

6. Verify Nginx configuration

```
nginx -t
```

7. Verify production is using the correct file.

---

## 10. Non Goals

- No manual edits directly inside running Docker containers.
- No force pushing directly into production branches.
- No editing generated files inside Docker images.
- No deployment from feature branches.
- Avoid unnecessary Docker rebuilds when only application data changes.

---

## 11. Production Principle

Production is always a reflection of the latest commit on:

```
origin/main
```

The deployment process should be deterministic, repeatable, and recoverable.
