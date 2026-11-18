from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from models.db import (cambiar_password, intentos_fallidos, registrar_acceso,
                       usuario_por_email)
from utils.seguridad import (comprobar_password, comprobar_password_falso, destino_seguro,
                             error_password, hash_password)

auth_bp = Blueprint('auth', __name__)

MAX_INTENTOS = 5      # fallos seguidos permitidos
VENTANA_MINUTOS = 15  # y durante cuánto tiempo se bloquea el email

MENSAJE_GENERICO = "Email o contraseña incorrectos."


def _ip():
    return request.remote_addr


@auth_bp.route('/login', methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('vehiculos.index'))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if email and intentos_fallidos(email, VENTANA_MINUTOS) >= MAX_INTENTOS:
            registrar_acceso(email, "login_bloqueado", _ip())
            flash(f"Demasiados intentos fallidos. Espera {VENTANA_MINUTOS} minutos.", "danger")
            return render_template('login.html', email=email), 429

        usuario = usuario_por_email(email) if email else None
        if usuario is not None:
            correcto = comprobar_password(usuario.password_hash, password)
        else:
            comprobar_password_falso(password)
            correcto = False

        # mismo mensaje para email inexistente, contraseña errónea y cuenta desactivada
        if not correcto or not usuario.activo:
            registrar_acceso(email, "login_fallido", _ip())
            flash(MENSAJE_GENERICO, "danger")
            return render_template('login.html', email=email), 401

        login_user(usuario, remember=False)
        registrar_acceso(usuario.email, "login_ok", _ip())
        destino = destino_seguro(request.args.get("next"))
        return redirect(destino or url_for('vehiculos.index'))

    return render_template('login.html', email="")


@auth_bp.route('/logout', methods=["POST"])
@login_required
def logout():
    registrar_acceso(current_user.email, "logout", _ip())
    logout_user()
    flash("Sesión cerrada.", "success")
    return redirect(url_for('auth.login'))


@auth_bp.route('/cuenta/password', methods=["GET", "POST"])
@login_required
def cambiar_password_propia():
    obligatorio = current_user.debe_cambiar_password
    if request.method == "POST":
        actual = request.form.get("actual", "")
        nueva = request.form.get("nueva", "")
        repetida = request.form.get("repetida", "")

        if not comprobar_password(current_user.password_hash, actual):
            flash("La contraseña actual no es correcta.", "danger")
        elif nueva != repetida:
            flash("Las contraseñas nuevas no coinciden.", "danger")
        elif comprobar_password(current_user.password_hash, nueva):
            flash("La contraseña nueva debe ser distinta de la actual.", "danger")
        elif (problema := error_password(nueva, current_user.email)):
            flash(problema, "danger")
        else:
            cambiar_password(current_user.id, hash_password(nueva), False)
            flash("Contraseña actualizada.", "success")
            return redirect(url_for('vehiculos.index'))

    return render_template('cambiarPassword.html', obligatorio=obligatorio)
