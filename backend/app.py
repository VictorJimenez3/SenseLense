"""Create and configure the SenseLense Flask application."""
from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from models import db
from blueprints.api import api_bp
from blueprints.analysis import analysis_bp
from blueprints.ai import ai_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)
    db.init_app(app)

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(analysis_bp, url_prefix="/api")
    app.register_blueprint(ai_bp, url_prefix="/api")

    @app.route("/")
    def index():
        return jsonify({
            "message": "SenseLense Backend is Running",
            "version": "1.0.0",
        })

    with app.app_context():
        db.create_all()

    return app


app = create_app()
