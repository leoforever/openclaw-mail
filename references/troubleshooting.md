# Troubleshooting

Common issues and solutions for mail-client.

---

## Connection refused

**Error:** `Connection refused` or `No route to host`

**Causes:**
- Wrong server hostname
- Firewall blocking connection
- Server down

**Solutions:**
1. Verify server hostname:
   ```bash
   ping smtp.sina.com
   ping imap.sina.com
   ```

2. Check firewall:
   ```bash
   telnet smtp.sina.com 465
   telnet imap.sina.com 993
   ```

3. Verify ports (common ports):
   - SMTP: 465 (SSL), 587 (STARTTLS)
   - IMAP: 993 (SSL), 143 (STARTTLS)

---

## Authentication failed

**Error:** `Authentication failed` or `LOGIN failed`

**Causes:**
- Wrong password
- Using login password instead of app key
- Account locked

**Solutions:**
1. For 新浪邮箱，use **授权码** (authorization code), not login password
2. Get authorization code from: 邮箱设置 → POP3/SMTP/IMAP → 开启服务 → 获取授权码
3. Re-run setup: `python3 scripts/setup.py`

---

## IMAP folder not found

**Error:** `BAD command` or `folder does not exist`

**Solutions:**
1. List available folders:
   ```bash
   python3 scripts/mail.py folders
   ```

2. Use correct folder name (case-sensitive):
   - `INBOX` (not `Inbox` or `inbox`)
   - Some servers use localized names

---

## SMTP relay rejected

**Error:** `Relay access denied` or `Sender rejected`

**Causes:**
- `mail_from` doesn't match authenticated user
- Server requires authentication

**Solutions:**
1. Ensure `mail_from` in config.json matches `MAIL_USER`
2. Verify SMTP authentication is enabled

---

## Self-signed certificate (local servers only)

**Warning:** `Certificate verify failed`

**⚠️ Only for local/internal servers:**

```python
import ssl
context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE
```

**⚠️ Never disable certificate verification for public servers!**

---

## Rate limiting

**Error:** `Too many connections` or `Rate limit exceeded`

**Solutions:**
1. Reduce query frequency
2. Increase delay between requests
3. Check provider's rate limits

---

## Large attachments

**Error:** `Message too large`

**Solutions:**
1. Check provider's attachment size limit (usually 20-25MB)
2. Compress files before attaching
3. Use cloud storage links instead

---

## Getting help

If issues persist:
1. Check logs: `~/.openclaw/logs/`
2. Verify configuration: `python3 scripts/mail.py config`
3. Re-run setup: `python3 scripts/setup.py`

---

*Last updated: 2026-04-07*
