"""Contraseñas, redirecciones seguras y decoradores de permisos."""
import secrets
from functools import wraps
from urllib.parse import urlparse

from flask import abort
from flask_login import current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash

MIN_LONGITUD_PASSWORD = 10

# Hash de una contraseña inexistente. Se compara cuando el email no existe para que el
# login tarde lo mismo y no se pueda averiguar qué emails están dados de alta.
_HASH_FALSO = generate_password_hash(secrets.token_urlsafe(16))


def hash_password(password):
    return generate_password_hash(password)


def comprobar_password(hash_guardado, password):
    return check_password_hash(hash_guardado, password)


def comprobar_password_falso(password):
    check_password_hash(_HASH_FALSO, password)


def password_temporal():
    """Contraseña aleatoria para cuentas nuevas o reseteadas (se muestra una sola vez)."""
    return secrets.token_urlsafe(9)


def error_password(password, email=""):
    """Devuelve un mensaje si la contraseña no es aceptable, o None si lo es."""
    if len(password) < MIN_LONGITUD_PASSWORD:
        return f"La contraseña debe tener al menos {MIN_LONGITUD_PASSWORD} caracteres."
    if password.lower() == email.strip().lower():
        return "La contraseña no puede ser igual que el email."
    if password.isdigit() or password.isalpha():
        return "La contraseña debe combinar letras y números u otros caracteres."
    return None


def destino_seguro(destino):
    """Solo se admiten rutas internas como destino tras el login (evita redirecciones abiertas)."""
    if not destino:
        return None
    partes = urlparse(destino)
    if partes.scheme or partes.netloc or not destino.startswith("/") or destino.startswith("//"):
        return None
    if "\\" in destino:
        return None
    return destino


def permiso_requerido(permiso):
    """Exige sesión iniciada y un permiso concreto (el admin los tiene todos)."""
    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(*args, **kwargs):
            if not current_user.tiene_permiso(permiso):
                abort(403)
            return vista(*args, **kwargs)
        return envoltura
    return decorador


def admin_requerido(vista):
    @wraps(vista)
    @login_required
    def envoltura(*args, **kwargs):
        if not current_user.es_admin:
            abort(403)
        return vista(*args, **kwargs)
    return envoltura
