from __future__ import annotations
import os

from flask import Flask, render_template
from routes.vehicles import vehiculos_bp

def create_app() -> Flask:

    app = Flask(__name__)
    # necesaria para los mensajes flash; en producción debe venir del .env
    app.secret_key = os.getenv("SECRET_KEY", "clave-solo-para-desarrollo")

    # Registramos las rutas del Blueprint
    app.register_blueprint(vehiculos_bp)


    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    return app

app = create_app()