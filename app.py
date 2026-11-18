from __future__ import annotations

import os

import click
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFError, CSRFProtect

from models.db import (EmailDuplicado, crear_usuario, migrar,
                       set_usuario_actual, usuario_por_id)
from models.entities import PERMISOS, ROLES
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.vehicles import vehiculos_bp
from utils.seguridad import error_password, hash_password

login_manager = LoginManager()
csrf = CSRFProtect()

# vistas que se pueden abrir sin haber iniciado sesión
RUTAS_PUBLICAS = {"auth.login", "static"}
# lo único que puede hacer alguien obligado a cambiar su contraseña
RUTAS_CAMBIO_PASSWORD = {"auth.cambiar_password_propia", "auth.logout", "static"}


@login_manager.user_loader
def cargar_usuario(id):
    try:
        return usuario_por_id(int(id))
    except (TypeError, ValueError):
        return None


def create_app() -> Flask:

    app = Flask(__name__)
    # necesaria para firmar la sesión y el token CSRF; en producción debe venir del .env
    app.secret_key = os.getenv("SECRET_KEY", "clave-solo-para-desarrollo")
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # en producción (HTTPS) poner SESSION_COOKIE_SECURE=1 en el .env
        SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE") == "1",
        PERMANENT_SESSION_LIFETIME=8 * 3600,
        WTF_CSRF_TIME_LIMIT=None,  # el token dura lo que la sesión
    )

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicia sesión para continuar."
    login_manager.login_message_category = "warning"
    login_manager.session_protection = "strong"
    csrf.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(vehiculos_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def ayudantes_permisos():
        # puede("costes.ver") en las plantillas; falso si no hay sesión
        def puede(permiso):
            return current_user.is_authenticated and current_user.tiene_permiso(permiso)
        return {"puede": puede, "PERMISOS": PERMISOS, "ROLES": ROLES}

    @app.before_request
    def exigir_login():
        # quién hace la petición, para que los triggers de auditoría lo registren
        set_usuario_actual(current_user.email if current_user.is_authenticated else None)

        if request.endpoint is None or request.endpoint in RUTAS_PUBLICAS:
            return None
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if current_user.debe_cambiar_password and request.endpoint not in RUTAS_CAMBIO_PASSWORD:
            flash("Debes elegir una contraseña propia antes de continuar.", "warning")
            return redirect(url_for("auth.cambiar_password_propia"))
        return None

    @app.teardown_request
    def olvidar_usuario(exc):
        set_usuario_actual(None)

    @app.errorhandler(CSRFError)
    def csrf_caducado(e):
        flash("El formulario ha caducado o no es válido. Vuelve a intentarlo.", "danger")
        return redirect(request.referrer or url_for("vehiculos.index"))

    @app.errorhandler(403)
    def prohibido(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    # ---- comandos: flask --app app migrar / crear-admin ----
    @app.cli.command("migrar")
    def comando_migrar():
        """Actualiza la base de datos (tablas, columnas y triggers) sin borrar datos."""
        set_usuario_actual("sistema:cli")
        migrar()

    @app.cli.command("crear-admin")
    @click.argument("email")
    @click.option("--nombre", prompt="Nombre", help="Nombre del administrador")
    @click.password_option(help="Contraseña del administrador")
    def comando_crear_admin(email, nombre, password):
        """Crea una cuenta de administrador (la primera, o más desde la terminal)."""
        problema = error_password(password, email)
        if problema:
            raise click.ClickException(problema)
        set_usuario_actual("sistema:cli")
        try:
            # la contraseña la eligió él mismo, no hace falta obligarle a cambiarla
            crear_usuario(email, nombre, "admin", [], hash_password(password), debe_cambiar=False)
        except EmailDuplicado:
            raise click.ClickException("Ya existe un usuario con ese email.")
        click.echo(f"Administrador {email} creado.")

    return app

app = create_app()
