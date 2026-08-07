import os
import socket
from flask import Flask, jsonify, render_template

app = Flask(__name__)

APP_NAME = os.getenv("APP_NAME", "Cloudnautic EKS Application")
APP_ENV = os.getenv("APP_ENV", "development")
APP_PASSWORD = os.getenv("APP_PASSWORD", "not-configured")


@app.route("/")
def home():
    return render_template(
        "index.html",
        app_name=APP_NAME,
        app_env=APP_ENV,
        hostname=socket.gethostname()
    )


@app.route("/api/info")
def api_info():
    return jsonify(
        {
            "message": "Application successfully deployed on Amazon EKS",
            "application": APP_NAME,
            "environment": APP_ENV,
            "hostname": socket.gethostname()
        }
    )


@app.route("/health")
def health():
    return jsonify(
        {
            "status": "healthy"
        }
    ), 200


@app.route("/secret-status")
def secret_status():
    return jsonify(
        {
            "secretConfigured": APP_PASSWORD != "not-configured"
        }
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000
    )
