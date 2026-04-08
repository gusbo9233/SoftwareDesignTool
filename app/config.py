import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
    SCREEN_MATERIALS_DIR = os.environ.get(
        "SCREEN_MATERIALS_DIR",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "screen_materials"),
    )
    STITCH_API_KEY = os.environ.get("STITCH_API_KEY", "")
    STITCH_API_URL = os.environ.get("STITCH_API_URL", "https://stitch.googleapis.com/mcp")
    STITCH_AUTH_TOKEN = os.environ.get("STITCH_ACCESS_TOKEN", "")
    STITCH_GCP_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    STITCH_NODE_BINARY = os.environ.get("STITCH_NODE_BINARY", "node")
    STITCH_BRIDGE_SCRIPT = os.environ.get(
        "STITCH_BRIDGE_SCRIPT",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "scripts", "stitch_bridge.mjs"),
    )


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True


config = {
    "default": DevelopmentConfig,
    "development": DevelopmentConfig,
    "testing": TestingConfig,
}
