from flask import Blueprint, request

api_bp = Blueprint("api", __name__)


@api_bp.post("/echo")
def echo():
    payload = request.get_json(silent=True)
    return {"echo": payload}
