import textwrap
import json

from api.classes import EmailData

def get_phishing_detection_prompt(email: EmailData) -> str:
    body = json.dumps(email.body)[1:-1]

    return textwrap.dedent(f"""
        You are a senior cybersecurity analyst with 15+ years of experience.
        Your goal: classify the email below with extremely low false positives.

        === RECIPIENT CONTEXT ===
        Recipient name  : {email.recipient_name or 'Not provided'}
        Recipient email : {email.recipient_email or 'Not provided'}

        === EMAIL DETAILS ===
        Sender Display Name : {email.sender_name or 'Not provided'}
        Sender Email        : {email.sender_email or 'Not provided'}
        Subject             : {email.subject}

        Full email body:
        \"{body}\"

        === CLASSIFICATION RULES (follow exactly) ===
        CLASSIFY AS "phishing" ONLY if ONE OR MORE of these are present:
        • Urgency/threats (account locked, payment overdue, legal action)
        • Requests to click links + login / reset password / enter credentials
        • Requests to download attachments or enable macros
        • Obvious domain spoofing and.or typosquatting in sender email
        • Unexpected requests for sensitive info (SSN, credit card, etc)
        • Generic greetings without recipient's name

        CLASSIFY AS "legit" (even if salesy) when:
        • Official welcome/onboarding emails from real services
        • Sent to the user's actual email address/name
        • Upgrade offers, privacy tips, newsletters from known companies
        • No dangerous CTAs

        Return ONLY this valid JSON (no markdown, no extra text):

        {{
          "verdict": "phishing" or "legit",
          "confidence": "high" | "medium" | "low",
          "reasons": ["max 5 very short bullets"],
        }}
    """).strip()