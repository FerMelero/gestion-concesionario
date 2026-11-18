import re

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from models.db import (EmailDuplicado, accesos_recientes, actualizar_usuario, cambiar_password,
                       crear_usuario, informacion_audit_usuarios, listar_usuarios,
                       usuario_por_id)
from models.entities import PERMISOS, PERMISOS_EMPLEADO_POR_DEFECTO, ROLES
from utils.seguridad import admin_requerido, hash_password, password_temporal

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

EMAIL_VALIDO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _permisos_enviados():
    # solo se aceptan permisos del catálogo
    return [p for p in request.form.getlist("permisos") if p in PERMISOS]


def _leer_alta(form):
    email = form.get("email", "").strip().lower()
    nombre = form.get("nombre", "").strip()
    rol = form.get("rol", "empleado")
    if not EMAIL_VALIDO.match(email) or len(email) > 120:
        raise ValueError("El email no es válido.")
    if not nombre or len(nombre) > 80:
        raise ValueError("El nombre es obligatorio (máximo 80 caracteres).")
    if rol not in ROLES:
        raise ValueError("Rol no válido.")
    return email, nombre, rol


@admin_bp.route('/usuarios')
@admin_requerido
def usuarios():
    return render_template('admin/usuarios.html', usuarios=listar_usuarios())


@admin_bp.route('/usuarios/nuevo', methods=["GET", "POST"])
@admin_requerido
def nuevo_usuario():
    valores = {"email": "", "nombre": "", "rol": "empleado",
               "permisos": list(PERMISOS_EMPLEADO_POR_DEFECTO)}
    if request.method == "POST":
        valores = {"email": request.form.get("email", ""), "nombre": request.form.get("nombre", ""),
                   "rol": request.form.get("rol", "empleado"), "permisos": _permisos_enviados()}
        try:
            email, nombre, rol = _leer_alta(request.form)
            temporal = password_temporal()
            crear_usuario(email, nombre, rol, valores["permisos"], hash_password(temporal))
        except EmailDuplicado:
            flash("Ya existe un usuario con ese email.", "danger")
        except ValueError as e:
            flash(str(e), "danger")
        else:
            # la contraseña se muestra en esta respuesta y no se guarda en la sesión
            return render_template('admin/credenciales.html', email=email, nombre=nombre,
                                   password=temporal, nuevo=True)
    return render_template('admin/usuarioForm.html', usuario=None, valores=valores)


@admin_bp.route('/usuarios/<int:id>', methods=["GET", "POST"])
@admin_requerido
def editar_usuario(id):
    usuario = usuario_por_id(id)
    if usuario is None:
        abort(404)

    valores = {"nombre": usuario.nombre, "rol": usuario.rol, "activo": usuario.activo,
               "permisos": sorted(usuario.codigos_permisos)}
    if request.method == "POST":
        valores = {"nombre": request.form.get("nombre", ""), "rol": request.form.get("rol", ""),
                   "activo": request.form.get("activo") == "on", "permisos": _permisos_enviados()}
        try:
            if not valores["nombre"].strip() or len(valores["nombre"]) > 80:
                raise ValueError("El nombre es obligatorio (máximo 80 caracteres).")
            if valores["rol"] not in ROLES:
                raise ValueError("Rol no válido.")
            actualizar_usuario(id, valores["nombre"], valores["rol"], valores["activo"],
                               valores["permisos"], actor_id=current_user.id)
        except ValueError as e:
            flash(str(e), "danger")
        else:
            flash("Cambios guardados.", "success")
            return redirect(url_for('admin.usuarios'))
    return render_template('admin/usuarioForm.html', usuario=usuario, valores=valores)


@admin_bp.route('/usuarios/<int:id>/reset', methods=["POST"])
@admin_requerido
def resetear_password(id):
    usuario = usuario_por_id(id)
    if usuario is None:
        abort(404)
    if usuario.id == current_user.id:
        flash("Tu propia contraseña se cambia desde «Mi contraseña».", "danger")
        return redirect(url_for('admin.usuarios'))
    temporal = password_temporal()
    cambiar_password(usuario.id, hash_password(temporal), True)
    return render_template('admin/credenciales.html', email=usuario.email, nombre=usuario.nombre,
                           password=temporal, nuevo=False)


@admin_bp.route('/historial')
@admin_requerido
def historial():
    return render_template('admin/historial.html', cambios=informacion_audit_usuarios(),
                           accesos=accesos_recientes())
