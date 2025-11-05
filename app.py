from flask import Flask, render_template, request, jsonify
import email
import os
import random # Import the random module

app = Flask(__name__)

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
            
            def get_decoded_header(header_name):
                header = msg[header_name]
                if header is None:
                    return ""
                decoded_header = email.header.decode_header(header)
                header_parts = []
                for part, charset in decoded_header:
                    if isinstance(part, bytes):
                        header_parts.append(part.decode(charset or 'utf-8', errors='ignore'))
                    else:
                        header_parts.append(part)
                return "".join(header_parts)

            def get_body(msg):
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        if content_type == "text/html" and "attachment" not in content_disposition:
                            try:
                                return part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                            except (UnicodeDecodeError, AttributeError):
                                continue
                    # Fallback to plain text if no html body is found
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            try:
                                return f"<pre>{part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')}</pre>"
                            except (UnicodeDecodeError, AttributeError):
                                continue
                else:
                    try:
                        return msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='ignore')
                    except (UnicodeDecodeError, AttributeError):
                        return "Could not decode body"
                return "No body found"

            is_phishing = random.random() < 0.5 # 50% chance of being phishing

            result = {
                'filename': file.filename,
                'subject': get_decoded_header('Subject'),
                'from': get_decoded_header('From'),
                'to': get_decoded_header('To'),
                'date': get_decoded_header('Date'),
                'body': get_body(msg),
                'analytics': {
                    'spf': 'pass',
                    'dkim': 'pass',
                    'dmarc': 'pass',
                    'links': [],
                    'attachments': [],
                    'is_phishing': is_phishing # Add phishing flag
                }
            }
            results.append(result)
        except Exception as e:
            results.append({
                'filename': file.filename,
                'error': str(e)
            })
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
