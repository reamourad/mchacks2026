from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "mchacks2026"

    # Auth0
    auth0_domain: str = ""
    auth0_audience: str = ""
    auth0_algorithms: list[str] = ["RS256"]

    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-2"
    aws_s3_bucket: str = ""

    # Session
    session_secret: str = "change-me-in-production"
    session_cookie_name: str = "session_id"

    # CORS
    frontend_url: str = "http://localhost:3000"

    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"  # Default: Rachel voice

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra env variables not defined here


@lru_cache()
def get_settings() -> Settings:
    return Settings()
