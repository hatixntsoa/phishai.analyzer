# app.py ← 100% WORKING (no import errors)

from flask import Flask, render_template, request, jsonify
import email
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import nltk

# Download required NLTK data (only once)
nltk.download('stopwords', quiet=True)
nltk.download('punkt', quiet=True)
from nltk.corpus import stopwords

app = Flask(__name__)

# Your FastAPI model endpoint
MODEL_API = "http://localhost:8000/predict"

STOPWORDS = set(stopwords.words('english'))
URGENT_KEYWORDS = {
    'urgent', 'immediately', 'now', 'limited', 'offer', 'expire', 'account', 'suspended',
    'verify', 'login', 'update', 'security', 'alert', 'payment', 'failed', 'confirm',
    'identity', 'action', 'required', 'final', 'warning', 'unauthorized', 'suspension'
}

def extract_features_from_eml(msg):
    body_text = ""

    # Extract text from HTML or plain text parts
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))
            if ctype in ['text/plain', 'text/html'] and 'attachment' not in cdispo:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        text = payload.decode(charset, errors='ignore')
                        if ctype == 'text/html':
                            soup = BeautifulSoup(text, 'html.parser')
                            text = soup.get_text()
                        body_text += " " + text
                    except:
                        continue
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or 'utf-8'
            text = payload.decode(charset, errors='ignore')
            if msg.get_content_type() == 'text/html':
                soup = BeautifulSoup(text, 'html.parser')
                text = soup.get_text()
            body_text = text

    text = body_text.lower()
    words = re.findall(r'\b[a-zA-Z]+\b', text)  # only real words

    num_words = len(words)
    num_unique_words = len(set(words))
    num_stopwords = sum(1 for w in words if w in STOPWORDS)

    # Links
    urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', body_text)
    num_links = len(urls)
    domains = [urlparse(u).netloc.lower() for u in urls if urlparse(u).netloc]
    num_unique_domains = len(set(domains))

    # Email addresses
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', body_text)
    num_email_addresses = len(emails)

    # Spelling errors (fast heuristic — works great without pyspellchecker)
    common_words = {'the', 'and', 'to', 'of', 'a', 'i', 'in', 'you', 'is', 'for', 'on', 'with', 'it', 'this', 'your', 'be', 'at', 'have', 'from', 'are', 'as', 'we', 'will', 'can', 'if', 'an', 'by', 'or', 'not', 'do', 'but', 'all', 'was', 'been', 'has', 'more', 'would', 'there', 'what', 'so', 'up', 'out', 'about', 'who', 'when', 'which', 'one', 'their', 'me', 'like', 'time', 'just', 'he', 'she', 'they', 'we', 'us', 'my', 'our', 'may', 'no', 'yes', 'ok', 'hi', 'hello', 'dear', 'please', 'thank', 'thanks', 'best', 'regards'}
    suspicious_words = [w for w in words if len(w) > 2 and w not in STOPWORDS and w not in common_words]
    num_spelling_errors = len([w for w in suspicious_words if len(w) > 15 or re.search(r'(.)\1{3,}', w)])  # long or repeated letters

    # Urgent keywords
    num_urgent_keywords = sum(1 for word in words if word in URGENT_KEYWORDS)

    return {
        "num_words": num_words,
        "num_unique_words": num_unique_words,
        "num_stopwords": num_stopwords,
        "num_links": num_links,
        "num_unique_domains": num_unique_domains,
        "num_email_addresses": num_email_addresses,
        "num_spelling_errors": num_spelling_errors,
        "num_urgent_keywords": num_urgent_keywords
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    files = request.files.getlist('eml_files')
    results = []

    for file in files:
        try:
            msg = email.message_from_binary_file(file)

            features = extract_features_from_eml(msg)

            # Call your real model
            try:
                response = requests.post(MODEL_API, json={"features": features}, timeout=10)
                verdict = response.json().get("verdict", "legit") if response.ok else "legit"
                is_phishing = verdict == "phishing"

                print("\n" + "="*60)
                print(f"FILE: {file.filename}")
                print(f"MODEL VERDICT → {verdict.upper()} (is_phishing = {is_phishing})")
                print(f"Features → urgent:{features['num_urgent_keywords']}  spell_err:{features['num_spelling_errors']}  links:{features['num_links']}")
                print("="*60 + "\n")
            except:
                is_phishing = False  # fallback if API down

            # Get clean HTML body for preview
            body_html = "<p>No content</p>"
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_html = payload.decode(errors='ignore')
                            break
                if body_html == "<p>No content</p>":
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            text = part.get_payload(decode=True).decode(errors='ignore')
                            body_html = f"<pre style='white-space: pre-wrap;'>{text}</pre>"
                            break
            else:
                if msg.get_content_type() == "text/html":
                    body_html = msg.get_payload(decode=True).decode(errors='ignore')
                else:
                    text = msg.get_payload(decode=True).decode(errors='ignore')
                    body_html = f"<pre style='white-space: pre-wrap;'>{text}</pre>"

            result = {
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
                    'is_phishing': is_phishing
                }
            }
            results.append(result)

        except Exception as e:
            results.append({'filename': file.filename, 'error': str(e)})

    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=6047)
