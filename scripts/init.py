#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mail Client Initialization - Validate configuration
"""

import imaplib
import smtplib
import sys
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent))
from mail import MailClient


def check(name, condition):
    """Print check result"""
    status = "✅ OK" if condition else "❌ FAIL"
    print(f"  {status}: {name}")
    return condition


def main():
    print("="*60)
    print("📧 Mail Client - Initialization Check")
    print("="*60)
    print()
    
    client = MailClient()
    all_ok = True
    
    print("📁 Configuration:")
    all_ok &= check("Config file exists", (Path.home() / ".openclaw" / "config" / "mail-client" / "config.json").exists())
    all_ok &= check("Credentials file exists", (Path.home() / ".openclaw" / "secrets" / "mail_creds").exists())
    
    print()
    print("🔐 Credentials:")
    all_ok &= check("MAIL_USER configured", bool(client.user))
    all_ok &= check("MAIL_APP_KEY configured", bool(client.app_key))
    all_ok &= check("MAIL_SMTP_HOST configured", bool(client.smtp_host))
    all_ok &= check("MAIL_IMAP_HOST configured", bool(client.imap_host))
    
    print()
    print("🔌 Network:")
    
    # Test IMAP
    try:
        imap = imaplib.IMAP4_SSL(client.imap_host, client.imap_port)
        imap.socket().settimeout(5)
        imap.login(client.user, client.app_key)
        imap.logout()
        all_ok &= check(f"IMAP ({client.imap_host}:{client.imap_port})", True)
    except Exception as e:
        all_ok &= check(f"IMAP ({client.imap_host}:{client.imap_port})", False)
        print(f"     Error: {e}")
    
    # Test SMTP
    try:
        smtp = smtplib.SMTP_SSL(client.smtp_host, client.smtp_port, timeout=5)
        smtp.login(client.user, client.app_key)
        smtp.quit()
        all_ok &= check(f"SMTP ({client.smtp_host}:{client.smtp_port})", True)
    except Exception as e:
        all_ok &= check(f"SMTP ({client.smtp_host}:{client.smtp_port})", False)
        print(f"     Error: {e}")
    
    print()
    print("🔐 Capabilities:")
    all_ok &= check("allow_send", client.allow_send)
    all_ok &= check("allow_read", client.allow_read)
    all_ok &= check("allow_search", client.allow_search)
    
    print()
    print("="*60)
    if all_ok:
        print("✅ All checks passed!")
    else:
        print("⚠️  Some checks failed. Review configuration.")
    print("="*60)
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
