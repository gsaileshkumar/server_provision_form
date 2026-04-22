import os


class Config:
    mongo_uri: str = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    mongo_db: str = os.environ.get("MONGO_DB", "server_provision")
    host: str = os.environ.get("FORM_API_HOST", "0.0.0.0")
    port: int = int(os.environ.get("FORM_API_PORT", "5001"))
