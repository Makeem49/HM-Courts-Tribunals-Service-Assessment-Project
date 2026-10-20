"""Pytest fixtures."""

import pytest

from app import create_app
from app.extensions import db


@pytest.fixture()
def app():
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret",
    })
    with application.app_context():
        db.drop_all()
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def valid_task():
    return {
        "title": "Review case documents",
        "description": "Check the latest submission.",
        "status": "pending",
        "due_at": "2030-10-20T15:00:00Z",
    }
