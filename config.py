"""Application configuration."""

import os


class Config:
    """Default configuration for the task manager."""

    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///hmcts_tasks.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
