# PROJECT_SPEC_deployment.md

## 1. Core Purpose

This document defines the deployment architecture, production environment, update workflow, and operational procedures for the BuyTelegramBots platform (website + Telegram sales bots).

It serves as the reference for deploying, updating, debugging, and maintaining the production server.

---

## 2. Production Environment

### Server

- Ubuntu 24.04 LTS
- Hetzner VPS (`rashid-ubuntu-4gb`)
- Root access
- SSH deployment

> **Shared server:** this VPS also hosts other, unrelated sites and apps behind the same Nginx and the same `ufw` firewall. Never change server-wide settings (firewall rules, global Nginx config) for BuyTelegramBots alone — restrict changes to this project's files and its own Nginx site file (`/etc/nginx/sites-enabled/buytelegrambots-web`).

### Reverse Proxy

- Cloudflare (DNS + proxy) in front of the server; `buytelegrambots.com` redirects to `www.buytelegrambots.com`
- Nginx
- HTTPS via Let's Encrypt (Certbot)

### Runtime

Python 3.12, systemd services (no Docker).

Virtual environments

```
/opt/buytelegrambots-web/web/.venv     # website
/opt/buytelegrambots-web/bot/.venv     # Telegram bots
```

---

## 3. Repository Layout

```
/opt/buytelegrambots-web

├── bot/                 # 18 Telegram sales bots (aiogram)
├── web/                 # website (FastAPI)
├── deploy/              # copies of the production systemd service files
├── docs/
└── README.md
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
fix/*
```

Production always tracks:

```
origin/main
```

---

## 4. Production Services

There are exactly **two** services. Their definitions are kept in `deploy/` and must stay identical to the copies in `/etc/systemd/system/`.

| | Website | Telegram bots |
|---|---|---|
| systemd service | `buytelegrambots-web` | `gram-bid-system` (the project's original name) |
| Definition | `deploy/buytelegrambots-web.service` | `deploy/gram-bid-system.service` |
| Runs | `web/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8004` | `bot/.venv/bin/python main.py` |
| Working directory | `/opt/buytelegrambots-web/web` | `/opt/buytelegrambots-web/bot` |
| Secrets | `web/.env` (via `EnvironmentFile`) | `bot/.env` (read by the bot via python-dotenv) |
| Data | none (offers go straight to Telegram) | `bot/bids.db` (SQLite: bids + live negotiations) |
| Auto-restart | `Restart=always`, `RestartSec=5` | `Restart=always`, `RestartSec=5` |
| Public? | only through Nginx → `127.0.0.1:8004` | no port; talks to Telegram by long-polling |

Nginx Proxy

```
Cloudflare → Nginx :443 → 127.0.0.1:8004 (buytelegrambots-web)
```

### Bots: things to know

- **One process runs all 18 bots.** Stopping or restarting `gram-bid-system` affects every bot at once.
- **Restarts lose nothing.** Messages buyers send while the bot is down or restarting are kept by Telegram (up to 24h) and answered when it is back (`drop_pending_updates=False` in `bot/main.py`).
- **A buyer in the middle of typing an offer** starts that step again after a restart (FSM state is in memory). Live chats and saved offers are in `bot/bids.db` and survive restarts.
- **Never run a second copy** of the bots (e.g. `python main.py` by hand while the service is running): Telegram allows only one poller per bot and both copies will error.

### Installing or changing a service file

```
cp deploy/<name>.service /etc/systemd/system/<name>.service
systemctl daemon-reload
systemctl enable <name>
systemctl restart <name>
```

---

## 5. Deployment Workflow

### Step 1 — Update the server's copy of the code

```
cd /opt/buytelegrambots-web

git status                 # must show no modified tracked files; if it does, stop and investigate
git fetch origin
git reset --hard origin/main
git log --oneline -1       # confirm the expected commit
```

`git reset --hard` never touches `.env` files, `.venv/` or `bot/bids.db` (they are git-ignored).

> **Never run `git clean -x`** (or `-X`) in `/opt/buytelegrambots-web`: it deletes git-ignored files — the `.env` files, the virtual environments and the bots' database. Plain `git clean -n` / `git clean -f` (without `x`) is safe.

### Step 2 — Restart what changed

| Changed files | Restart |
|---|---|
| anything in `web/` | `systemctl restart buytelegrambots-web` |
| anything in `bot/` | `systemctl restart gram-bid-system` |
| `web/requirements.txt` | `web/.venv/bin/pip install -r web/requirements.txt`, then restart the website |
| `bot/requirements.txt` | `bot/.venv/bin/pip install -r bot/requirements.txt`, then restart the bots |
| a file in `deploy/` | see "Installing or changing a service file" above |
| only `docs/` or `README.md` | nothing |

### Step 3 — Verify (section 6)

---

## 6. Service Verification

Website

```
systemctl status buytelegrambots-web --no-pager
journalctl -u buytelegrambots-web -n 100 --no-pager
curl -s -o /dev/null -w "%{http_code}\n" https://www.buytelegrambots.com/        # 200
curl -s -o /dev/null -w "%{http_code}\n" https://www.buytelegrambots.com/.env    # 404
```

Bots

```
systemctl status gram-bid-system --no-pager
journalctl -u gram-bid-system -n 60 --no-pager    # 18 lines "Added @... to portfolio", then "Start polling"
ps aux | grep "[b]ot/.venv/bin/python main.py"     # exactly ONE process
```

Nginx

```
nginx -t
```

---

## 7. Backups and Rollback

Before any change that touches the bots or their data:

```
cp /opt/buytelegrambots-web/bot/bids.db /root/bids.db.$(date +%F-%H%M).bak
```

Roll back code to the previous commit:

```
cd /opt/buytelegrambots-web
git log --oneline -5                 # find the last good commit
git reset --hard <commit>
systemctl restart buytelegrambots-web gram-bid-system
```

Restore the bots' database (only if it was damaged):

```
systemctl stop gram-bid-system
cp /root/bids.db.<date>.bak /opt/buytelegrambots-web/bot/bids.db
systemctl start gram-bid-system
```

---

## 8. Deployment Rules

Never edit files directly on production unless performing emergency debugging.

Production must always mirror:

```
origin/main
```

All code changes must go through a branch and a reviewed pull request into `main`:

```
feature/* or fix/*
        ↓
pull request → main
```

---

## 9. File Responsibilities

> **Public vs private:** only files inside `web/static/` can be downloaded by visitors. Everything else in `web/` (including `.env`) is private. Never put secrets in `web/static/`.

static/bots.json

Purpose

Homepage inventory cards. Also the list of usernames the web form accepts (`bot_username` validation).

Changing this file updates:

- homepage descriptions
- homepage cards
- which usernames the web form accepts

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

Static Assets (public, in `web/static/`)

```
static/index.html
static/styles.css
static/script.js
static/favicon.png
```

Restart service after modification.

---

bot/.env

Purpose

Bot tokens (`BOT_TOKENS`, one per listed username) and the admin group (`GROUP_CHAT_ID`). Adding or removing a token adds or removes a bot from the running set and from the "Other Available Usernames" list.

Requires

```
systemctl restart gram-bid-system
```

---

bot/bids.db

Purpose

The bots' data: every offer and every live negotiation (which admin-group topic belongs to which buyer). Not in git. Back it up before risky changes (section 7).

---

## 10. Troubleshooting Checklist

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

3. Restart the right service (section 5, step 2)

4. Verify the service (section 6)

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

If a bot does not answer:

1. `systemctl status gram-bid-system --no-pager` — is it `active (running)`?
2. `journalctl -u gram-bid-system -n 100 --no-pager` — look for `Traceback`, `Unauthorized` (token revoked/wrong) or `Conflict` (a second copy is running).
3. `ps aux | grep "[b]ot/.venv/bin/python main.py"` — exactly one process.

---

## 11. Non Goals

- No Docker. Both services run directly under systemd.
- No force pushing directly into production branches.
- No deployment from feature branches.
- No server-wide firewall or Nginx changes for this project (the server is shared).

---

## 12. Production Principle

Production is always a reflection of the latest commit on:

```
origin/main
```

The deployment process should be deterministic, repeatable, and recoverable.
