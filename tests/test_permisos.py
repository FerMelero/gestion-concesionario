from conftest import DATOS_VEHICULO, admin, empleado_con, nuevo_usuario, entrar, sql  # noqa: F401
from models.db import insert_vehicle


def _vehiculo():
    from datetime import datetime
    insert_vehicle({
        "marca": "Seat", "modelo": "Ibiza", "vin": "VSSZZZ6JZ9R000001", "kilometros": 5000.0,
        "anio": datetime(2020, 1, 1), "fecha_entrada": datetime(2024, 1, 1), "motor": "G",
        "cilindrada": 1000, "consumo": 5.5, "potencia": 95, "transmision": "Manual", "marchas": 5,
        "precio_compra": 8000.0, "precio_venta": 10000.0, "estado": "D"})
    return sql("SELECT id FROM vehiculo")[0]["id"]


def test_empleado_basico_solo_consulta(client):
    id_ = _vehiculo()
    empleado_con(client)  # sin permisos
    assert client.get("/").status_code == 200
    assert client.get(f"/vehiculos/{id_}").status_code == 200
    assert client.get("/nuevo").status_code == 403
    assert client.post("/nuevo", data=DATOS_VEHICULO).status_code == 403
    assert client.get(f"/vehiculos/modificar/{id_}").status_code == 403
    assert client.post(f"/vehiculos/eliminar/{id_}").status_code == 403
    assert client.get("/vehiculos/auditoria").status_code == 403
    assert client.get("/resumen").status_code == 403
    assert client.get("/admin/usuarios").status_code == 403
    assert len(sql("SELECT id FROM vehiculo")) == 1


def test_cada_permiso_abre_solo_lo_suyo(client):
    id_ = _vehiculo()
    empleado_con(client, "vehiculos.crear")
    assert client.post("/nuevo", data=DATOS_VEHICULO).status_code == 302
    assert client.get(f"/vehiculos/modificar/{id_}").status_code == 403
    assert client.post(f"/vehiculos/eliminar/{id_}").status_code == 403


def test_eliminar_con_permiso(client):
    id_ = _vehiculo()
    empleado_con(client, "vehiculos.eliminar")
    assert client.post(f"/vehiculos/eliminar/{id_}").status_code == 302
    assert sql("SELECT id FROM vehiculo") == []


def test_los_botones_dependen_de_los_permisos(client):
    _vehiculo()
    empleado_con(client)
    html = client.get("/").get_data(as_text=True)
    assert "Añadir vehículo" not in html and "Eliminar" not in html and ">Auditoría<" not in html
    client.post("/logout")
    nuevo_usuario("jefe@test.com", rol="admin")
    entrar(client, "jefe@test.com")
    html = client.get("/").get_data(as_text=True)
    assert "Añadir vehículo" in html and "Usuarios" in html and "Auditoría" in html


def test_sin_costes_no_se_ven_ni_se_tocan(client):
    id_ = _vehiculo()
    empleado_con(client, "vehiculos.editar")
    ficha = client.get(f"/vehiculos/{id_}").get_data(as_text=True)
    assert "Precio de compra" not in ficha and "Margen" not in ficha
    formulario = client.get(f"/vehiculos/modificar/{id_}").get_data(as_text=True)
    assert 'name="pCompra"' not in formulario

    datos = {k: v for k, v in DATOS_VEHICULO.items() if k not in ("pCompra", "vin")}
    datos["pVenta"] = "11000"
    assert client.post(f"/vehiculos/modificar/{id_}", data=datos).status_code == 302
    fila = sql("SELECT precio_compra, precio_venta FROM vehiculo")[0]
    assert fila["precio_compra"] == 8000.0 and fila["precio_venta"] == 11000.0


def test_con_costes_se_ven(client):
    id_ = _vehiculo()
    empleado_con(client, "costes.ver")
    assert "Precio de compra" in client.get(f"/vehiculos/{id_}").get_data(as_text=True)


def test_auditoria_oculta_costes_sin_permiso(client):
    _vehiculo()
    empleado_con(client, "auditoria.ver")
    html = client.get("/vehiculos/auditoria").get_data(as_text=True)
    assert "C: 8,000.00" not in html and "V: 10,000.00" in html
    client.post("/logout")
    empleado_con(client, "auditoria.ver", "costes.ver", email="otro@test.com")
    assert "C: 8,000.00" in client.get("/vehiculos/auditoria").get_data(as_text=True)


def test_resumen_con_permiso_y_acceso_registrado(client):
    _vehiculo()
    empleado_con(client, "resumen.ver")
    r = client.get("/resumen")
    assert r.status_code == 200 and "Resumen económico" in r.get_data(as_text=True)
    assert "acceso_resumen" in [f["evento"] for f in sql("SELECT evento FROM registro_acceso")]


def test_venta_rellena_fecha_y_precio_final(client):
    id_ = _vehiculo()
    empleado_con(client, "vehiculos.editar", "costes.ver")
    datos = {k: v for k, v in DATOS_VEHICULO.items() if k != "vin"}
    datos["estado"] = "V"
    assert client.post(f"/vehiculos/modificar/{id_}", data=datos).status_code == 302
    fila = sql("SELECT fecha_venta, precio_final FROM vehiculo")[0]
    assert fila["fecha_venta"] is not None and fila["precio_final"] == 12000.0
    datos["estado"] = "D"
    client.post(f"/vehiculos/modificar/{id_}", data=datos)
    fila = sql("SELECT fecha_venta, precio_final FROM vehiculo")[0]
    assert fila["fecha_venta"] is None and fila["precio_final"] is None
