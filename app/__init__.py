"""Flask application factory."""

from flask import Flask, jsonify, render_template
from werkzeug.exceptions import HTTPException

from app.extensions import db


def create_app(test_config=None):
    """Create and configure a Flask application instance."""
    app = Flask(
        __name__,
        template_folder="../frontend",
        static_folder="../frontend",
        static_url_path="/static",
    )
    app.config.from_object("config.Config")
    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    from app.api.tasks import tasks_bp

    app.register_blueprint(tasks_bp)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify({"error": error.name, "message": error.description}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception("Unexpected application error")
        return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred."}), 500

    with app.app_context():
        db.create_all()

    return app
