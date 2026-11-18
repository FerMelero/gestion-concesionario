"""Los tests usan SIEMPRE una base de datos aparte (por defecto concesionario_test),
nunca la de desarrollo: hay que crearla antes (CREATE DATABASE concesionario_test)."""
import os
import sys

# debe ir antes de importar la app: config.py lee el nombre de la base de datos del entorno
os.environ["dbname"] = os.getenv("TEST_DBNAME", "concesionario_test")
assert os.environ["dbname"].endswith("_test"), "TEST_DBNAME debe terminar en _test para no tocar datos reales"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import text

from app import app as flask_app
from models.db import crear_usuario, engine, migrar
from models.entities import Base
from utils.seguridad import hash_password

PASSWORD = "Clave-de-prueba-1"


@pytest.fixture(scope="session", autouse=True)
def esquema():
    Base.metadata.drop_all(engine)
    migrar()
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def tablas_limpias():
    with engine.begin() as conn:
        conn.execute(text(
            "TRUNCATE vehiculo, usuario, usuario_permiso, audit_vehiculo, audit_usuario, "
            "registro_acceso RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def app():
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def nuevo_usuario(email, rol="empleado", permisos=(), temporal=False, activo=True):
    """Crea un usuario de prueba directamente en la base de datos."""
    id_ = crear_usuario(email, email.split("@")[0], rol, list(permisos), hash_password(PASSWORD),
                        debe_cambiar=temporal)
    if not activo:
        with engine.begin() as conn:
            conn.execute(text("UPDATE usuario SET activo = false WHERE id = :i"), {"i": id_})
    return id_


def entrar(client, email, password=PASSWORD):
    return client.post("/login", data={"email": email, "password": password})


@pytest.fixture
def admin(client):
    nuevo_usuario("admin@test.com", rol="admin")
    entrar(client, "admin@test.com")
    return client


def empleado_con(client, *permisos, email="emp@test.com"):
    nuevo_usuario(email, permisos=permisos)
    entrar(client, email)
    return client


DATOS_VEHICULO = {
    "marca": "Audi", "modelo": "A3", "vin": "WAUZZZ8V0JA123456", "kilometros": "10000",
    "anio": "2019-01-01", "fEntrada": "2024-01-01", "motor": "G", "cilindrada": "1998",
    "consumo": "6.5", "potencia": "150", "transmision": "Manual", "marchas": "6",
    "pCompra": "10000", "pVenta": "12000", "estado": "D",
}


def sql(consulta, **params):
    with engine.connect() as conn:
        return conn.execute(text(consulta), params).mappings().all()
