# FILE: app.py - Main entry point. Starts the Flask server. Don't touch unless adding core features.
from flask import Flask
from flask_cors import CORS

from config import Config
from models import db


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)
    db.init_app(app)

    from blueprints.api import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    with app.app_context():
        db.create_all()

    return app


app = create_app()
