from typing import Dict, Any
from fastapi import FastAPI

import ollama
import re

from api.classes import *

app = FastAPI()

OLLAMA_MODEL = "phi3:mini"

def analyze_with_ollama(email: EmailData) -> Dict[str, Any]:
    sender_email = email.sender_email.strip().lower()
    match = re.search(r"@([\w\.-]+)", sender_email)
    sender_domain = match.group(1) if match else ""
    sender_username = sender_email.split("@")[0]

    prompt = f"""
You are an expert phishing email detector working for a corporate security team.
Analyze the email below and return strict, accurate JSON only.

**Email Details**:
Sender Display Name: {email.sender_name or 'None'}
Sender Email Address: {email.sender_email}
Subject: {email.subject}
Body: {email.body}

**Instructions**:
- Analyze the email carefully.
- Return JSON only, with no extra text.

**Output Format**:
{{
  "verdict": "phishing" or "legit",
  "confidence": "high" | "medium" | "low",
  "reasons": ["short bullet points explaining why"]
}}
"""

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0}
            # NOTE :the lower the temperature,
            # the more the model is deterministic
        )
        raw = response['message']['content'].strip()

        # Try to extract JSON (in case model adds extra text)
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            import json
            result = json.loads(json_match.group(0))
        else:
            result = {"verdict": "phishing", "confidence": "low", "reasons": ["Model response unclear"]}

        result["verdict"] = result["verdict"].lower()
        if "phish" in result["verdict"]:
            result["verdict"] = "phishing"
        elif "legit" in result["verdict"] or "safe" in result["verdict"]:
            result["verdict"] = "legit"

        return result

    except Exception as e:
        return {
            "verdict": "phishing",
            "confidence": "low",
            "reasons": [f"Ollama error: {str(e)}"]
        }

@app.post("/predict")
async def predict(request: PredictRequest):
    results = []
    for email in request.emails:
        result = analyze_with_ollama(email)
        results.append({
            "sender": email.sender_email,
            "subject": email.subject,
            "verdict": result["verdict"],
            "confidence": result.get("confidence", "medium"),
            "reasons": result.get("reasons", [])
        })

    return {"verdicts": results}
