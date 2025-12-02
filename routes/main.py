from flask import Blueprint, render_template, request, jsonify
from services.email_parser import extract_email_data
from services.model_client import batch_predict
from email.policy import default

import email

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/analyze', methods=['POST'])
def analyze():
    files = request.files.getlist('eml_files')
    results = []
    emails_batch = []

    for file in files:
        try:
            msg = email.message_from_binary_file(file.stream, policy=default)
            email_data, body_html = extract_email_data(msg)
            emails_batch.append(email_data)

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

    if emails_batch:
        try:
            verdicts = batch_predict(emails_batch)
            for i, verdict_data in enumerate(verdicts):
                if i < len(results):
                    results[i]['analytics'].update({
                        'is_phishing': verdict_data['verdict'] == 'phishing',
                        'confidence': verdict_data.get('confidence', 'medium'),
                        'reasons': verdict_data.get('reasons', [])
                    })
        except Exception as e:
            print(f"Failed to reach model API: {e}")

    return jsonify(results)
