from __future__ import annotations
from flask import Flask, redirect, render_template, request, session, url_for
from routes.vehicles import vehiculos_bp

def create_app() -> Flask:

    app = Flask(__name__)

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