from flask import current_app
import requests

def batch_predict(emails_batch):
    if not emails_batch:
        return []

    try:
        response = requests.post(
            current_app.config['MODEL_API'],
            json={"emails": emails_batch},
            # timeout=60
        )
        if response.status_code == 200:
            return response.json().get("verdicts", [])
        else:
            print(f"API error {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to reach model API: {e}")

    return []
