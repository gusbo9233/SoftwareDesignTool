import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
    STITCH_API_URL = os.environ.get("STITCH_API_URL", "https://mcp.stitch.withgoogle.com/v1")
    STITCH_AUTH_TOKEN = os.environ.get("STITCH_ACCESS_TOKEN", "")
    STITCH_GCP_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True


config = {
    "default": DevelopmentConfig,
    "development": DevelopmentConfig,
    "testing": TestingConfig,
}
