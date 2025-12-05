from typing import Tuple, Dict, List
from email.policy import default
from bs4 import BeautifulSoup
from html import escape

import email
import re

def extract_email_data(msg) -> Tuple[Dict, str]:
    from_header = msg.get("From", "")
    sender_name = None
    sender_email = from_header

    parsed = email.utils.parseaddr(from_header)
    if parsed[0]:
        sender_name = parsed[0]
        sender_email = parsed[1]
    else:
        match = re.search(r'<([^>]+)>', from_header)
        if match:
            sender_email = match.group(1)
            sender_name = from_header.replace(f"<{sender_email}>", "").strip().strip('"\'')
        else:
            match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', from_header)
            sender_email = match.group(0) if match else from_header

    to_header = msg.get("To", "")
    recipient_name = None
    recipient_email = to_header

    parsed_to = email.utils.parseaddr(to_header)
    if parsed_to[0]:
        recipient_name = parsed_to[0]
        recipient_email = parsed_to[1]
    else:
        match_to = re.search(r'<([^>]+)>', to_header)
        if match_to:
            recipient_email = match_to.group(1)
            recipient_name = to_header.replace(f"<{recipient_email}>", "").strip().strip('"\'')
        else:
            match_to = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', to_header)
            recipient_email = match_to.group(0) if match_to else to_header

    subject = msg.get("Subject", "(no subject)")

    body_text = ""
    body_html = "<p>No content</p>"

    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))

            if ctype == "text/plain" and 'attachment' not in cdispo:
                payload = part.get_payload(decode=True)
                if payload:
                    body_text += payload.decode(errors='ignore') + "\n"

            if ctype == "text/html" and 'attachment' not in cdispo:
                payload = part.get_payload(decode=True)
                if payload:
                    body_html = payload.decode(errors='ignore')
                    soup = BeautifulSoup(body_html, 'html.parser')
                    body_text += soup.get_text(separator='\n') + "\n"
        if (not body_html or body_html.strip() == "<p>No content</p>") and body_text.strip():
            body_html = f"<pre style='white-space: pre-wrap;'>{escape(body_text.strip())}</pre>"
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            text = payload.decode(errors='ignore')
            if msg.get_content_type() == "text/html":
                body_html = text
                soup = BeautifulSoup(text, 'html.parser')
                body_text = soup.get_text(separator='\n')
            else:
                body_text = text
                body_html = f"<pre style='white-space: pre-wrap;'>{text}</pre>"

    attachment_filenames = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get("Content-Disposition") and 'attachment' in str(part.get("Content-Disposition")):
                filename = part.get_filename()
                if filename:
                    attachment_filenames.append(filename)

    email_data = {
        "sender_name": sender_name,
        "sender_email": sender_email.lower(),
        "recipient_name": recipient_name,
        "recipient_email": recipient_email.lower(),
        "subject": subject,
        "body": body_text.strip(),
        "attachment_filenames": attachment_filenames
    }

    return email_data, body_html