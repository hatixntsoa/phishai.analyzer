class Config:
    MODEL_API = "http://localhost:8000/predict"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'eml'}
