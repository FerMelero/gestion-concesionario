import re

from conftest import DATOS_VEHICULO, PASSWORD, admin, empleado_con, entrar, nuevo_usuario, sql  # noqa: F401


def _crear_empleado(client, email="nuevo@test.com", permisos=("vehiculos.crear",)):
    r = client.post("/admin/usuarios/nuevo", data={
        "email": email, "nombre": "Nuevo", "rol": "empleado", "permisos": list(permisos)})
    assert r.status_code == 200, r.get_data(as_text=True)
    return re.search(r"<code>([^<]+)</code>", r.get_data(as_text=True)).group(1)


def test_admin_crea_empleado_con_contrasena_temporal(admin, app):
    temporal = _crear_empleado(admin)
    fila = sql("SELECT rol, debe_cambiar_password FROM usuario WHERE email = 'nuevo@test.com'")[0]
    assert fila["rol"] == "empleado" and fila["debe_cambiar_password"] is True
    assert [f["permiso"] for f in sql("SELECT permiso FROM usuario_permiso")] == ["vehiculos.crear"]

    otro = app.test_client()
    assert entrar(otro, "nuevo@test.com", temporal).status_code == 302
    r = otro.get("/")
    assert r.status_code == 302 and "/cuenta/password" in r.headers["Location"]


def test_email_duplicado_y_datos_invalidos(admin):
    _crear_empleado(admin)
    r = admin.post("/admin/usuarios/nuevo", data={"email": "NUEVO@test.com", "nombre": "X", "rol": "empleado"})
    assert "Ya existe un usuario con ese email" in r.get_data(as_text=True)
    r = admin.post("/admin/usuarios/nuevo", data={"email": "no-es-email", "nombre": "X", "rol": "empleado"})
    assert "El email no es válido" in r.get_data(as_text=True)
    r = admin.post("/admin/usuarios/nuevo", data={"email": "a@b.com", "nombre": "X", "rol": "superman"})
    assert "Rol no válido" in r.get_data(as_text=True)


def test_permisos_inventados_se_ignoran(admin):
    _crear_empleado(admin, permisos=("vehiculos.crear", "usuarios.gestionar", "x"))
    assert [f["permiso"] for f in sql("SELECT permiso FROM usuario_permiso")] == ["vehiculos.crear"]


def test_editar_permisos_y_desactivar(admin, app):
    _crear_empleado(admin)
    id_ = sql("SELECT id FROM usuario WHERE email = 'nuevo@test.com'")[0]["id"]
    r = admin.post(f"/admin/usuarios/{id_}", data={
        "nombre": "Nuevo", "rol": "empleado", "activo": "on", "permisos": ["vehiculos.editar", "costes.ver"]})
    assert r.status_code == 302
    assert sorted(f["permiso"] for f in sql("SELECT permiso FROM usuario_permiso")) == ["costes.ver", "vehiculos.editar"]
    admin.post(f"/admin/usuarios/{id_}", data={"nombre": "Nuevo", "rol": "empleado", "permisos": []})
    assert sql("SELECT activo FROM usuario WHERE id = :i", i=id_)[0]["activo"] is False


def test_no_se_puede_dejar_sin_administradores(admin):
    id_admin = sql("SELECT id FROM usuario WHERE email = 'admin@test.com'")[0]["id"]
    # a sí mismo
    r = admin.post(f"/admin/usuarios/{id_admin}", data={"nombre": "A", "rol": "empleado", "activo": "on"})
    assert "No puedes quitarte" in r.get_data(as_text=True)
    r = admin.post(f"/admin/usuarios/{id_admin}", data={"nombre": "A", "rol": "admin"})
    assert "No puedes quitarte" in r.get_data(as_text=True)
    assert sql("SELECT rol, activo FROM usuario WHERE id = :i", i=id_admin)[0] == {"rol": "admin", "activo": True}


def test_degradar_a_otro_admin_deja_al_menos_uno(app):
    a = nuevo_usuario("a@test.com", rol="admin")
    b = nuevo_usuario("b@test.com", rol="admin")
    c = app.test_client()
    entrar(c, "a@test.com")
    # degradar a b está permitido (queda a)
    assert c.post(f"/admin/usuarios/{b}", data={"nombre": "B", "rol": "empleado", "activo": "on"}).status_code == 302
    # queda a como único administrador activo
    assert sql("SELECT count(*) AS n FROM usuario WHERE rol='admin' AND activo")[0]["n"] == 1


def test_resetear_contrasena(admin, app):
    _crear_empleado(admin)
    id_ = sql("SELECT id FROM usuario WHERE email = 'nuevo@test.com'")[0]["id"]
    r = admin.post(f"/admin/usuarios/{id_}/reset")
    nueva = re.search(r"<code>([^<]+)</code>", r.get_data(as_text=True)).group(1)
    otro = app.test_client()
    assert entrar(otro, "nuevo@test.com", nueva).status_code == 302
    # no se puede resetear la propia
    id_admin = sql("SELECT id FROM usuario WHERE email = 'admin@test.com'")[0]["id"]
    r = admin.post(f"/admin/usuarios/{id_admin}/reset", follow_redirects=True)
    assert "Mi contraseña" in r.get_data(as_text=True)


def test_auditoria_de_usuarios_no_guarda_el_hash(admin):
    _crear_empleado(admin)
    filas = sql("""SELECT user_id, tabla, operacion, datos_nuevos::text AS nuevos FROM audit_usuario
                   WHERE usuario_id = (SELECT id FROM usuario WHERE email = 'nuevo@test.com') ORDER BY id""")
    assert {f["user_id"] for f in filas} == {"admin@test.com"}
    assert {f["tabla"] for f in filas} == {"usuario", "usuario_permiso"}
    assert all("password_hash" not in (f["nuevos"] or "") for f in filas)

    id_ = sql("SELECT id FROM usuario WHERE email = 'nuevo@test.com'")[0]["id"]
    admin.post(f"/admin/usuarios/{id_}/reset")
    ultimo = sql("SELECT datos_nuevos::text AS nuevos FROM audit_usuario ORDER BY id DESC LIMIT 1")[0]
    assert "password_cambiada" in ultimo["nuevos"] and "scrypt" not in ultimo["nuevos"]


def test_auditoria_de_vehiculos_guarda_el_usuario_de_la_app(client):
    empleado_con(client, "vehiculos.crear", "vehiculos.editar", "vehiculos.eliminar")
    client.post("/nuevo", data=DATOS_VEHICULO)
    id_ = sql("SELECT id FROM vehiculo")[0]["id"]
    datos = {k: v for k, v in DATOS_VEHICULO.items() if k != "vin"}
    datos["pVenta"] = "13000"
    client.post(f"/vehiculos/modificar/{id_}", data=datos)
    client.post(f"/vehiculos/eliminar/{id_}")

    filas = sql("SELECT operacion, user_id, precio_venta, datos_anteriores FROM audit_vehiculo ORDER BY id")
    assert [f["operacion"] for f in filas] == ["I", "U", "D"]
    assert {f["user_id"] for f in filas} == {"emp@test.com"}
    assert filas[0]["datos_anteriores"] is None
    assert filas[1]["datos_anteriores"]["precio_venta"] == 12000.0 and filas[1]["precio_venta"] == 13000.0


def test_el_usuario_no_se_filtra_entre_peticiones(app):
    a = app.test_client()
    empleado_con(a, "vehiculos.crear", email="uno@test.com")
    a.post("/nuevo", data=DATOS_VEHICULO)
    b = app.test_client()
    empleado_con(b, "vehiculos.crear", email="dos@test.com")
    b.post("/nuevo", data={**DATOS_VEHICULO, "vin": "WAUZZZ8V0JA654321"})
    usuarios = [f["user_id"] for f in sql("SELECT user_id FROM audit_vehiculo ORDER BY id")]
    assert usuarios == ["uno@test.com", "dos@test.com"]


def test_historial_solo_para_admin(client, admin):
    assert admin.get("/admin/historial").status_code == 200
    admin.post("/logout")
    empleado_con(client, "auditoria.ver")
    assert client.get("/admin/historial").status_code == 403
