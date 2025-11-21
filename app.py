# app.py — FINAL VERSION (Ollama-powered via FastAPI backend)
from flask import Flask, render_template, request, jsonify
import email
import re
from email.policy import default
import requests

app = Flask(__name__)

# Your FastAPI Ollama backend (running on uvicorn)
MODEL_API = "http://localhost:8000/predict"

def extract_email_data(msg):
    """Extract everything the LLM needs from .eml"""
    # Sender: parse display name and email
    from_header = msg.get("From", "")
    sender_name = None
    sender_email = from_header

    # Try to extract display name <email>
    import email.utils
    parsed = email.utils.parseaddr(from_header)
    if parsed[0]:  # name exists
        sender_name = parsed[0]
        sender_email = parsed[1]
    else:
        # Fallback: try to get email from angle brackets
        match = re.search(r'<([^>]+)>', from_header)
        if match:
            sender_email = match.group(1)
            sender_name = from_header.replace(f"<{sender_email}>", "").strip().strip('"\'')
        else:
            # Last resort: whole thing is email
            match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', from_header)
            sender_email = match.group(0) if match else from_header

    subject = msg.get("Subject", "(no subject)")

    # Body extraction (HTML → clean text for LLM, keep HTML for preview)
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
                    # Also extract clean text from HTML
                    try:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(body_html, 'html.parser')
                        body_text += soup.get_text(separator='\n') + "\n"
                    except:
                        pass
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            text = payload.decode(errors='ignore')
            if msg.get_content_type() == "text/html":
                body_html = text
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(text, 'html.parser')
                    body_text = soup.get_text(separator='\n')
                except:
                    body_text = text
            else:
                body_text = text
                body_html = f"<pre style='white-space: pre-wrap;'>{text}</pre>"

    # Attachments
    attachment_filenames = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get("Content-Disposition") and 'attachment' in str(part.get("Content-Disposition")):
                filename = part.get_filename()
                if filename:
                    attachment_filenames.append(filename)

    return {
        "sender_name": sender_name,
        "sender_email": sender_email.lower(),
        "subject": subject,
        "body": body_text.strip(),
        "attachment_filenames": attachment_filenames
    }, body_html

## This is header email logic, do not touch
## may include false positives, maybe next feature :)
#
# def check_authentication_results(msg):
#     """Check Authentication-Results header. If any check exists and is not PASS → phishing"""
#     auth_header = msg.get("Authentication-Results", "")
#     if not auth_header:
#         return "fail", "fail", "fail"  # No auth header at all → phishing
#
#     auth_lower = auth_header.lower()
#
#     spf = dkim = dmarc = "unknown"
#
#     # Detect presence and result
#     if "spf=pass" in auth_lower:
#         spf = "pass"
#     elif "spf=" in auth_lower:  # spf= exists but not pass → fail, neutral, etc.
#         spf = "fail"
#
#     if "dkim=pass" in auth_lower:
#         dkim = "pass"
#     elif "dkim=" in auth_lower:
#         dkim = "fail"
#
#     if "dmarc=pass" in auth_lower:
#         dmarc = "pass"
#     elif "dmarc=" in auth_lower:
#         dmarc = "fail"
#
#     # Final rule: if ANY check exists and is NOT "pass" → phishing
#     if (spf != "unknown" and spf != "pass") or \
#        (dkim != "unknown" and dkim != "pass") or \
#        (dmarc != "unknown" and dmarc != "pass"):
#         return "fail", "fail", "fail"
#
#     # Otherwise: either all pass, or no checks performed → let model decide
#     return spf, dkim, dmarc
#
#
# @app.route('/analyze', methods=['POST'])
# def analyze():
#     files = request.files.getlist('eml_files')
#     results = []
#     emails_batch = []  # Only for emails that need model analysis
#
#     for file in files:
#         try:
#             msg = email.message_from_binary_file(file, policy=default)
#             email_data, body_html = extract_email_data(msg)
#
#             # === SPF/DKIM/DMARC CHECK ===
#             spf, dkim, dmarc = check_authentication_results(msg)
#
#             # Auto-flag as phishing if any fail or missing
#             if spf == "fail" or dkim == "fail" or dmarc == "fail":
#                 is_phishing = True
#                 confidence = "high"
#                 reasons = ["Failed email authentication (SPF/DKIM/DMARC missing or failed)"]
#             else:
#                 # Let the model decide
#                 emails_batch.append(email_data)
#                 is_phishing = False
#                 confidence = ""
#                 reasons = []
#
#             results.append({
#                 'filename': file.filename,
#                 'subject': msg.get('Subject', '(no subject)'),
#                 'from': msg.get('From', ''),
#                 'to': msg.get('To', ''),
#                 'date': msg.get('Date', ''),
#                 'body': body_html,
#                 'analytics': {
#                     'spf': spf,
#                     'dkim': dkim,
#                     'dmarc': dmarc,
#                     'is_phishing': is_phishing,
#                     'confidence': confidence,
#                     'reasons': reasons
#                 }
#             })
#         except Exception as e:
#             results.append({
#                 'filename': file.filename,
#                 'error': f"Parse error: {str(e)}",
#                 'analytics': {'is_phishing': True, 'spf': 'fail', 'dkim': 'fail', 'dmarc': 'fail'}
#             })
#
#     # Only call model if there are emails that passed auth checks
#     if emails_batch:
#         try:
#             response = requests.post(MODEL_API, json={"emails": emails_batch}, timeout=60)
#             if response.status_code == 200:
#                 verdicts = response.json().get("verdicts", [])
#                 batch_idx = 0
#                 for i, result in enumerate(results):
#                     if not result['analytics']['is_phishing']:  # was waiting for model
#                         verdict_data = verdicts[batch_idx]
#                         result['analytics'].update({
#                             'is_phishing': verdict_data['verdict'] == 'phishing',
#                             'confidence': verdict_data.get('confidence', 'medium'),
#                             'reasons': verdict_data.get('reasons', [])
#                         })
#                         batch_idx += 1
#         except Exception as e:
#             print(f"Model API failed: {e}")
#
#     return jsonify(results)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    files = request.files.getlist('eml_files')
    results = []

    # Prepare batch for FastAPI
    emails_batch = []

    for file in files:
        try:
            # Parse .eml properly with policy
            msg = email.message_from_binary_file(file, policy=default)
            email_data, body_html = extract_email_data(msg)

            emails_batch.append(email_data)

            # Store preview data (we'll enrich with verdict later)
            results.append({
                'filename': file.filename,
                'subject': msg.get('Subject', '(no subject)'),
                'from': msg.get('From', ''),
                'to': msg.get('To', ''),
                'date': msg.get('Date', ''),
                'body': body_html,
                'analytics': {
                    'spf': 'unknown',
                    'dkim': 'unknown',
                    'dmarc': 'unknown',
                    'is_phishing': False,
                    'confidence': '',
                    'reasons': []
                }
            })
        except Exception as e:
            results.append({
                'filename': file.filename,
                'error': f"Parse error: {str(e)}",
                'analytics': {'is_phishing': False}
            })

    # === CALL YOUR OLLAMA FASTAPI BACKEND ===
    if emails_batch:
        try:
            response = requests.post(
                MODEL_API,
                json={"emails": emails_batch},
                timeout=60  # LLMs can take a few seconds
            )
            if response.status_code == 200:
                verdicts = response.json().get("verdicts", [])
                for i, verdict_data in enumerate(verdicts):
                    if i < len(results):
                        results[i]['analytics'].update({
                            'is_phishing': verdict_data['verdict'] == 'phishing',
                            'confidence': verdict_data.get('confidence', 'medium'),
                            'reasons': verdict_data.get('reasons', [])
                        })
            else:
                print(f"API error {response.status_code}: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to reach model API: {e}")
            # Don't crash — just mark as unknown

    return jsonify(results)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=6047)
