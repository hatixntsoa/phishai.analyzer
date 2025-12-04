from api.prompt import get_phishing_detection_prompt
from api.classes import *

from typing import Dict, Any
from fastapi import FastAPI

import json
import re
import os

from dotenv import load_dotenv
from google import genai
import ollama

app = FastAPI()

OLLAMA_MODEL = "phi3:mini"
GEMINI_MODEL = "gemini-2.5-flash"

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

gemini_client = genai.Client(api_key=API_KEY)


def ask_gemini(prompt: str) -> str:
    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return response.text.strip()


def ask_ollama(prompt: str) -> str:
    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0}
    )
    return response['message']['content'].strip()


def parse_model_response(raw: str) -> Dict[str, Any]:
    """
    Extract JSON from model raw text and normalize verdict/confidence/reasons.
    """
    try:
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(0))
        else:
            result = json.loads(raw)

        # normalize verdict
        result["verdict"] = str(result.get("verdict", "")).lower()
        if "phish" in result["verdict"]:
            result["verdict"] = "phishing"
        elif "legit" in result["verdict"] or "safe" in result["verdict"]:
            result["verdict"] = "legit"

        # ensure expected keys
        result.setdefault("confidence", "medium")
        result.setdefault("reasons", [])

        return result

    except Exception as e:
        return {
            "verdict": "phishing",
            "confidence": "low",
            "reasons": [f"Model parsing error: {str(e)}"]
        }


def analyze_email(email: EmailData) -> Dict[str, Any]:
    prompt = get_phishing_detection_prompt(email)

    try:
        raw = ask_gemini(prompt)
        result = parse_model_response(raw)
        return result
    except Exception:
        try:
            raw = ask_ollama(prompt)
            result = parse_model_response(raw)
            return result
        except Exception as e:
            return {
                "verdict": "phishing",
                "confidence": "low",
                "reasons": [f"Both model calls failed: {str(e)}"]
            }


@app.post("/predict")
async def predict(request: PredictRequest):
    results = []
    for email in request.emails:
        result = analyze_email(email)
        results.append({
            "sender": email.sender_email,
            "subject": email.subject,
            "verdict": result["verdict"],
            "confidence": result.get("confidence", "medium"),
            "reasons": result.get("reasons", [])
        })

    return {"verdicts": results}