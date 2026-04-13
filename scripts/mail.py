#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mail Client - IMAP/SMTP mail client for OpenClaw
Python stdlib only, zero external dependencies.
"""

import imaplib
import smtplib
import email
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders, header
from email.header import decode_header
import os
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any


class MailClient:
    """IMAP/SMTP mail client"""
    
    def __init__(self, config_dir: str = None, secrets_dir: str = None):
        self.config_dir = Path(config_dir) if config_dir else Path.home() / ".openclaw" / "config" / "mail-client"
        self.secrets_dir = Path(secrets_dir) if secrets_dir else Path.home() / ".openclaw" / "secrets"
        
        self.config = self._load_config()
        self.creds = self._load_creds()
        
        # Config values
        self.smtp_host = self.creds.get("MAIL_SMTP_HOST", "smtp.sina.com")
        self.imap_host = self.creds.get("MAIL_IMAP_HOST", "imap.sina.com")
        self.user = self.creds.get("MAIL_USER", "")
        self.app_key = self.creds.get("MAIL_APP_KEY", "")
        self.smtp_port = self.config.get("smtp_port", 465)
        self.imap_port = self.config.get("imap_port", 993)
        self.mail_from = self.config.get("mail_from", self.user)
        self.default_folder = self.config.get("default_folder", "INBOX")
        self.max_results = self.config.get("max_results", 20)
        
        # Capabilities
        self.allow_send = self.config.get("allow_send", False)
        self.allow_read = self.config.get("allow_read", False)
        self.allow_search = self.config.get("allow_search", False)
        self.allow_delete = self.config.get("allow_delete", False)
    
    def _load_config(self) -> Dict:
        """Load config from ~/.openclaw/config/mail-client/config.json"""
        config_file = self.config_dir / "config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _load_creds(self) -> Dict:
        """Load credentials from env vars or ~/.openclaw/secrets/mail_creds"""
        creds = {}
        
        # Check env vars first (take precedence)
        for key in ["MAIL_SMTP_HOST", "MAIL_IMAP_HOST", "MAIL_USER", "MAIL_APP_KEY"]:
            if os.environ.get(key):
                creds[key] = os.environ[key]
        
        # Fall back to creds file
        creds_file = self.secrets_dir / "mail_creds"
        if creds_file.exists() and creds_file.stat().st_mode & 0o777 == 0o600:
            with open(creds_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        if key not in creds:  # env vars take precedence
                            creds[key] = value.strip()
        
        return creds
    
    def _get_imap(self) -> imaplib.IMAP4_SSL:
        """Get IMAP connection"""
        if not self.user or not self.app_key:
            raise RuntimeError("Mail credentials not configured. Run: python3 scripts/setup.py")
        
        imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
        imap.login(self.user, self.app_key)
        return imap
    
    def _get_smtp(self) -> smtplib.SMTP_SSL:
        """Get SMTP connection"""
        if not self.user or not self.app_key:
            raise RuntimeError("Mail credentials not configured. Run: python3 scripts/setup.py")
        
        smtp = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
        smtp.login(self.user, self.app_key)
        return smtp
    
    def _decode_header(self, h) -> str:
        """Decode email header"""
        if not h:
            return ""
        decoded = decode_header(h)
        result = ""
        for part, enc in decoded:
            if isinstance(part, bytes):
                # Handle unknown encodings
                if enc in (None, "unknown-8bit", "unknown"):
                    try:
                        result += part.decode("utf-8", errors="ignore")
                    except:
                        result += part.decode("gbk", errors="ignore")
                else:
                    try:
                        result += part.decode(enc, errors="ignore")
                    except LookupError:
                        result += part.decode("utf-8", errors="ignore")
            else:
                result += str(part)
        return result
    
    def _get_body(self, msg: email.message.Message) -> str:
        """Extract plain text body from message"""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get("Content-Disposition"))
                if ctype == "text/plain" and "attachment" not in cdispo:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode("utf-8", errors="ignore")
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
            except:
                pass
        return body
    
    def list_messages(self, limit: int = None, unseen_only: bool = False, folder: str = None) -> List[Dict]:
        """List messages from mailbox"""
        if not self.allow_read:
            raise PermissionError("allow_read is False in config.json")
        
        limit = limit or self.max_results
        folder = folder or self.default_folder
        
        imap = self._get_imap()
        imap.select(folder)
        
        search_criteria = "UNSEEN" if unseen_only else "ALL"
        status, messages = imap.search(None, search_criteria)
        email_ids = messages[0].split()
        
        result = []
        for msg_id in reversed(email_ids[-limit:]):
            status, msg_data = imap.fetch(msg_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    result.append({
                        "uid": msg_id.decode(),
                        "from": self._decode_header(msg.get("From", "")),
                        "to": self._decode_header(msg.get("To", "")),
                        "subject": self._decode_header(msg.get("Subject", "")),
                        "date": msg.get("Date", ""),
                        "seen": "\\Seen" in str(msg_data)
                    })
        
        imap.close()
        imap.logout()
        return result
    
    def read_message(self, uid: str, folder: str = None) -> Dict:
        """Read full message by UID"""
        if not self.allow_read:
            raise PermissionError("allow_read is False in config.json")
        
        folder = folder or self.default_folder
        
        imap = self._get_imap()
        imap.select(folder)
        
        status, msg_data = imap.fetch(uid.encode(), "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        
        result = {
            "uid": uid,
            "from": self._decode_header(msg.get("From", "")),
            "to": self._decode_header(msg.get("To", "")),
            "subject": self._decode_header(msg.get("Subject", "")),
            "date": msg.get("Date", ""),
            "body": self._get_body(msg)
        }
        
        imap.close()
        imap.logout()
        return result
    
    def search_messages(self, from_addr: str = None, to_addr: str = None, 
                       subject: str = None, since: str = None, 
                       unseen_only: bool = False) -> List[Dict]:
        """Search messages with filters"""
        if not self.allow_search:
            raise PermissionError("allow_search is False in config.json")
        
        imap = self._get_imap()
        imap.select(self.default_folder)
        
        criteria_parts = []
        if unseen_only:
            criteria_parts.append("UNSEEN")
        if from_addr:
            criteria_parts.append(f'(FROM "{from_addr}")')
        if to_addr:
            criteria_parts.append(f'(TO "{to_addr}")')
        if subject:
            criteria_parts.append(f'(SUBJECT "{subject}")')
        if since:
            criteria_parts.append(f'(SINCE "{since}")')
        
        search_criteria = " ".join(criteria_parts) if criteria_parts else "ALL"
        
        status, messages = imap.search(None, search_criteria)
        email_ids = messages[0].split()
        
        result = []
        for msg_id in reversed(email_ids[-self.max_results:]):
            status, msg_data = imap.fetch(msg_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    result.append({
                        "uid": msg_id.decode(),
                        "from": self._decode_header(msg.get("From", "")),
                        "subject": self._decode_header(msg.get("Subject", "")),
                        "date": msg.get("Date", "")
                    })
        
        imap.close()
        imap.logout()
        return result
    
    def send(self, to: str, subject: str, body: str, 
             cc: str = None, attachments: List[str] = None, 
             html: bool = False) -> Dict:
        """Send an email"""
        if not self.allow_send:
            raise PermissionError("allow_send is False in config.json")
        
        msg = MIMEMultipart()
        msg['From'] = self.mail_from
        msg['To'] = to
        msg['Subject'] = subject
        
        if cc:
            msg['Cc'] = cc
        
        content_type = 'html' if html else 'plain'
        msg.attach(MIMEText(body, content_type, 'utf-8'))
        
        if attachments:
            for filepath in attachments:
                if os.path.exists(filepath):
                    filename = os.path.basename(filepath)
                    # Detect MIME type from file extension
                    mime_type, _ = mimetypes.guess_type(filepath)
                    if mime_type is None:
                        mime_type = 'application/octet-stream'
                    
                    maintype, subtype = mime_type.split('/', 1)
                    with open(filepath, "rb") as f:
                        part = MIMEBase(maintype, subtype)
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        # Set filename with proper encoding (RFC 2231)
                        part.add_header('Content-Disposition', 'attachment', filename=filename)
                        msg.attach(part)
        
        recipients = [to]
        if cc:
            recipients.extend(cc.split(','))
        
        smtp = self._get_smtp()
        smtp.sendmail(self.mail_from, recipients, msg.as_string())
        smtp.quit()
        
        return {"status": "sent", "to": to, "subject": subject}
    
    def list_folders(self) -> List[str]:
        """List IMAP folders"""
        if not self.allow_read:
            raise PermissionError("allow_read is False in config.json")
        
        imap = self._get_imap()
        status, folders = imap.list()
        imap.logout()
        
        return [f.decode().split(' "/" ')[-1] if ' "/" ' in f.decode() else f.decode() 
                for f in folders]
    
    def get_quota(self) -> Dict:
        """Get mailbox quota"""
        imap = self._get_imap()
        imap.select(self.default_folder)
        
        status, quota = imap.getquotaroot(self.default_folder)
        imap.logout()
        
        # Parse quota response (format varies by server)
        return {"status": "ok", "quota": str(quota)}


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description='Mail Client CLI')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # list command
    list_parser = subparsers.add_parser('list', help='List messages')
    list_parser.add_argument('--limit', type=int, default=10)
    list_parser.add_argument('--unseen', action='store_true')
    
    # read command
    read_parser = subparsers.add_parser('read', help='Read message')
    read_parser.add_argument('uid', help='Message UID')
    
    # search command
    search_parser = subparsers.add_parser('search', help='Search messages')
    search_parser.add_argument('--from-addr')
    search_parser.add_argument('--subject')
    search_parser.add_argument('--since')
    search_parser.add_argument('--unseen', action='store_true')
    
    # send command
    send_parser = subparsers.add_parser('send', help='Send email')
    send_parser.add_argument('--to', required=True)
    send_parser.add_argument('--subject', required=True)
    send_parser.add_argument('--body', required=True)
    send_parser.add_argument('--cc')
    send_parser.add_argument('--attachment', action='append')
    send_parser.add_argument('--html', action='store_true')
    
    # config command
    subparsers.add_parser('config', help='Show config')
    
    # folders command
    subparsers.add_parser('folders', help='List folders')
    
    # quota command
    subparsers.add_parser('quota', help='Get quota')
    
    args = parser.parse_args()
    
    client = MailClient()
    
    try:
        if args.command == 'list':
            msgs = client.list_messages(limit=args.limit, unseen_only=args.unseen)
            for m in msgs:
                print(f"[{m['uid']}] From: {m['from']} | Subject: {m['subject']}")
        
        elif args.command == 'read':
            msg = client.read_message(args.uid)
            print(f"From: {msg['from']}")
            print(f"Subject: {msg['subject']}")
            print(f"Date: {msg['date']}")
            print("\n" + "="*50 + "\n")
            print(msg['body'])
        
        elif args.command == 'search':
            msgs = client.search_messages(
                from_addr=args.from_addr,
                subject=args.subject,
                since=args.since,
                unseen_only=args.unseen
            )
            for m in msgs:
                print(f"[{m['uid']}] From: {m['from']} | Subject: {m['subject']}")
        
        elif args.command == 'send':
            result = client.send(
                to=args.to,
                subject=args.subject,
                body=args.body,
                cc=args.cc,
                attachments=args.attachment,
                html=args.html
            )
            print(f"✅ Email sent: {result}")
        
        elif args.command == 'config':
            print("Config:")
            print(f"  SMTP: {client.smtp_host}:{client.smtp_port}")
            print(f"  IMAP: {client.imap_host}:{client.imap_port}")
            print(f"  From: {client.mail_from}")
            print(f"  Capabilities: send={client.allow_send}, read={client.allow_read}, search={client.allow_search}")
        
        elif args.command == 'folders':
            folders = client.list_folders()
            for f in folders:
                print(f"  {f}")
        
        elif args.command == 'quota':
            quota = client.get_quota()
            print(f"Quota: {quota}")
        
        else:
            parser.print_help()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
