#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mail Client Setup Wizard - Interactive configuration
"""

import os
import json
import sys
from pathlib import Path
import stat


def setup_wizard():
    """Interactive setup wizard"""
    print("="*60)
    print("📧 Mail Client Setup Wizard")
    print("="*60)
    print()
    
    config_dir = Path.home() / ".openclaw" / "config" / "mail-client"
    secrets_dir = Path.home() / ".openclaw" / "secrets"
    
    # Create directories
    config_dir.mkdir(parents=True, exist_ok=True)
    secrets_dir.mkdir(parents=True, exist_ok=True)
    
    print("📝 Enter your mail server configuration:")
    print("(Press Enter to use defaults for 新浪邮箱 loongsoncloud@sina.com)")
    print()
    
    # Get credentials
    default_user = "loongsoncloud@sina.com"
    user = input(f"Mail address [{default_user}]: ").strip() or default_user
    
    print()
    print("⚠️  For 新浪邮箱，use authorization code (授权码) not login password")
    print("   Get it from: 新浪邮箱设置 → POP3/SMTP/IMAP")
    default_key = "b2b1af13b41813b0"
    app_key = input(f"Authorization code [{default_key[:4]}...{default_key[-4:]}]: ").strip() or default_key
    
    print()
    print("📤 SMTP Configuration:")
    default_smtp = "smtp.sina.com"
    smtp_host = input(f"SMTP host [{default_smtp}]: ").strip() or default_smtp
    smtp_port = input("SMTP port [465]: ").strip() or "465"
    
    print()
    print("📥 IMAP Configuration:")
    default_imap = "imap.sina.com"
    imap_host = input(f"IMAP host [{default_imap}]: ").strip() or default_imap
    imap_port = input("IMAP port [993]: ").strip() or "993"
    
    print()
    print("🔐 Capabilities (enable features):")
    allow_send = input("  Allow sending emails? [y/N]: ").strip().lower() == 'y'
    allow_read = input("  Allow reading emails? [y/N]: ").strip().lower() == 'y'
    allow_search = input("  Allow searching emails? [y/N]: ").strip().lower() == 'y'
    allow_delete = input("  Allow deleting emails? [y/N]: ").strip().lower() == 'y'
    
    print()
    print("⚙️  Defaults:")
    default_folder = input("  Default folder [INBOX]: ").strip() or "INBOX"
    max_results = input("  Max results per query [20]: ").strip() or "20"
    
    # Write credentials (chmod 600)
    creds_file = secrets_dir / "mail_creds"
    with open(creds_file, 'w') as f:
        f.write(f"MAIL_SMTP_HOST={smtp_host}\n")
        f.write(f"MAIL_IMAP_HOST={imap_host}\n")
        f.write(f"MAIL_USER={user}\n")
        f.write(f"MAIL_APP_KEY={app_key}\n")
    
    # Set permissions to 600 (owner read/write only)
    os.chmod(creds_file, stat.S_IRUSR | stat.S_IWUSR)
    
    print(f"\n✅ Credentials saved to: {creds_file} (chmod 600)")
    
    # Write config
    config_file = config_dir / "config.json"
    config = {
        "smtp_port": int(smtp_port),
        "imap_port": int(imap_port),
        "mail_from": user,
        "default_folder": default_folder,
        "max_results": int(max_results),
        "allow_send": allow_send,
        "allow_read": allow_read,
        "allow_search": allow_search,
        "allow_delete": allow_delete
    }
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Config saved to: {config_file}")
    print()
    print("="*60)
    print("🎉 Setup complete!")
    print("="*60)
    print()
    print("Next steps:")
    print("  1. Run: python3 scripts/init.py  (validate configuration)")
    print("  2. Run: python3 scripts/mail.py list  (test reading)")
    print("  3. Run: python3 scripts/mail.py send  (test sending)")
    print()


def cleanup():
    """Remove credentials and config"""
    creds_file = Path.home() / ".openclaw" / "secrets" / "mail_creds"
    config_file = Path.home() / ".openclaw" / "config" / "mail-client" / "config.json"
    
    if creds_file.exists():
        creds_file.unlink()
        print(f"✅ Removed: {creds_file}")
    
    if config_file.exists():
        config_file.unlink()
        print(f"✅ Removed: {config_file}")
    
    print("✅ Cleanup complete")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
        cleanup()
    else:
        setup_wizard()
