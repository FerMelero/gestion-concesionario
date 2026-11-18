from contextvars import ContextVar
from datetime import datetime, timedelta

from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, or_, event, func
from sqlalchemy.exc import IntegrityError
import config
from models.entities import Base
from models.entities import (Vehiculo, AuditVehiculo, Usuario, UsuarioPermiso,
                             AuditUsuario, RegistroAcceso, PERMISOS)
# en este archivo es en el que se crean enn el servidor postgres

engine = config.engine
Session = sessionmaker(bind=engine)

class VinDuplicado(Exception):
    """Ya existe un vehículo con ese VIN."""


class EmailDuplicado(Exception):
    """Ya existe un usuario con ese email."""


# Usuario de la aplicación que está haciendo la petición. Antes de cada transacción se
# pasa a PostgreSQL (variable app.usuario) para que los triggers de auditoría guarden
# quién hizo el cambio y no el usuario con el que se conecta la aplicación.
_usuario_actual = ContextVar("usuario_actual", default=None)


def set_usuario_actual(email):
    _usuario_actual.set(email)


@event.listens_for(Session, "after_begin")
def _pasar_usuario_a_postgres(session, transaction, connection):
    email = _usuario_actual.get()
    if email:
        # el tercer argumento (true) limita el valor a la transacción en curso
        connection.exec_driver_sql("SELECT set_config('app.usuario', %s, true)", (email,))


def crear_tablas():
    print("Estableciendoconexión con Postgres")
    Base.metadata.create_all(engine)
    print("Tablas creadas")

ORDENES = {
    "id": Vehiculo.id,
    "marca": Vehiculo.marca,
    "precio": Vehiculo.precio_venta,
    "km": Vehiculo.kilometros,
    "anio": Vehiculo.anio,
    "entrada": Vehiculo.fecha_entrada,
}


def get_all_vehicles(page, per_page, filtros=None):
    """Devuelve una página de vehículos aplicando los filtros recibidos.

    Filtros admitidos: q (marca, modelo o VIN), estado, motor, precio_min,
    precio_max, km_max, orden y direccion ("asc" o "desc").
    """
    filtros = filtros or {}
    session = Session()
    try:
        query = session.query(Vehiculo)

        q = filtros.get("q")
        if q:
            patron = f"%{q}%"
            query = query.filter(or_(
                Vehiculo.marca.ilike(patron),
                Vehiculo.modelo.ilike(patron),
                Vehiculo.vin.ilike(patron),
            ))
        if filtros.get("estado"):
            query = query.filter(Vehiculo.estado == filtros["estado"])
        if filtros.get("motor"):
            query = query.filter(Vehiculo.motor == filtros["motor"])
        if filtros.get("precio_min") is not None or filtros.get("precio_max") is not None:
            # el CSV importado trae precios NaN; en Postgres NaN es mayor que cualquier número
            query = query.filter(Vehiculo.precio_venta != float("nan"))
        if filtros.get("precio_min") is not None:
            query = query.filter(Vehiculo.precio_venta >= filtros["precio_min"])
        if filtros.get("precio_max") is not None:
            query = query.filter(Vehiculo.precio_venta <= filtros["precio_max"])
        if filtros.get("km_max") is not None:
            query = query.filter(Vehiculo.kilometros <= filtros["km_max"])

        total = query.count()

        columna = ORDENES.get(filtros.get("orden"), Vehiculo.id)
        columna = columna.desc() if filtros.get("direccion") == "desc" else columna.asc()
        # el id como desempate mantiene la paginación estable
        items = (query.order_by(columna, Vehiculo.id)
                      .limit(per_page).offset((page - 1) * per_page).all())

        return {
            'items': items,
            'total': total,
            'page': page,
            'pages': max(1, (total + per_page - 1) // per_page),
        }
    finally:
        session.close()


def insert_vehicle(datos):
    """Inserta un vehículo a partir de un diccionario con los campos del modelo.

    Lanza ValueError si el modelo no valida los datos y VinDuplicado si el VIN ya existe.
    """
    session = Session()
    try:
        session.add(Vehiculo(**datos))
        session.commit()
    except IntegrityError as e:
        session.rollback()
        raise VinDuplicado(datos.get("vin")) from e
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def vehicle_by_id(id):
    session = Session()
    try:
        return session.query(Vehiculo).filter(Vehiculo.id == id).first()
    finally:
        session.close()


def delete_vehicle(id):
    """Borra el vehículo. Devuelve False si no existía."""
    session = Session()
    try:
        vehiculo = session.query(Vehiculo).filter(Vehiculo.id == id).first()
        if vehiculo is None:
            return False
        session.delete(vehiculo)
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def insert_masivo(lista_vehiculos):
    session = Session()

    try:
        session.add_all(lista_vehiculos)
        session.commit()
    
    except Exception as e:
        session.rollback()
        print("Error", e)

    finally:
        session.close()

def cambiar_cc_electricos():
    session = Session()
    try:
        session.query(Vehiculo).filter(Vehiculo.motor == "E").update({"cilindrada" : 0})
        session.commit() 
    except Exception as e:
        session.rollback()
        print("Error", e)
    finally:
        session.close()

def mod_vehiculo(id, datos_nuevos):
    """Modifica un vehículo asignando atributo a atributo, para que se ejecuten
    los validadores del modelo (con query.update() se saltarían).
    Devuelve False si el vehículo no existe."""
    session = Session()
    try:
        vehiculo = session.query(Vehiculo).filter(Vehiculo.id == id).first()
        if vehiculo is None:
            return False
        for campo, valor in datos_nuevos.items():
            setattr(vehiculo, campo, valor)
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def migrar():
    """Deja la base de datos al día sin borrar datos: crea las tablas que falten, añade
    las columnas nuevas y (re)crea los triggers de auditoría. Se puede lanzar varias veces."""
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE vehiculo ADD COLUMN IF NOT EXISTS fecha_venta TIMESTAMP"))
        conn.execute(text("ALTER TABLE vehiculo ADD COLUMN IF NOT EXISTS precio_final FLOAT"))
    crear_audits()
    print("Base de datos actualizada.")


def crear_audits():
    comandos = [
        "CREATE TABLE IF NOT EXISTS audit_vehiculo (operacion CHAR(1) NOT NULL, stamp TIMESTAMP NOT NULL, user_id VARCHAR(100) NOT NULL)",
        # columnas que pueden faltar si la tabla viene de una versión anterior
        "ALTER TABLE audit_vehiculo ADD COLUMN IF NOT EXISTS id BIGSERIAL",
        "ALTER TABLE audit_vehiculo ADD COLUMN IF NOT EXISTS fecha_venta TIMESTAMP",
        "ALTER TABLE audit_vehiculo ADD COLUMN IF NOT EXISTS precio_final FLOAT",
        "ALTER TABLE audit_vehiculo ADD COLUMN IF NOT EXISTS datos_anteriores JSONB",
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint
                           WHERE conrelid = 'audit_vehiculo'::regclass AND contype = 'p') THEN
                ALTER TABLE audit_vehiculo ADD PRIMARY KEY (id);
            END IF;
        END $$;
        """,
        """
        CREATE OR REPLACE FUNCTION fn_audit_vehiculo()
        RETURNS TRIGGER AS $$
        DECLARE
            r RECORD;
            anterior JSONB;
        BEGIN
            r := CASE WHEN (TG_OP = 'DELETE') THEN OLD ELSE NEW END;
            anterior := CASE WHEN (TG_OP = 'INSERT') THEN NULL ELSE to_jsonb(OLD) END;

            INSERT INTO audit_vehiculo (
                operacion, stamp, user_id, id_vehiculo, marca, modelo,
                kilometros, vin, anio, motor, cilindrada, consumo,
                marchas, transmision, precio_compra, precio_venta,
                fecha_entrada, estado, potencia, fecha_venta, precio_final,
                datos_anteriores
            )
            VALUES (
                SUBSTR(TG_OP, 1, 1),
                now(),
                COALESCE(NULLIF(current_setting('app.usuario', true), ''), current_user),
                r.id, r.marca, r.modelo,
                r.kilometros, r.vin, r.anio, r.motor, r.cilindrada, r.consumo,
                r.marchas, r.transmision, r.precio_compra, r.precio_venta,
                r.fecha_entrada, r.estado, r.potencia, r.fecha_venta, r.precio_final,
                anterior
            );
            RETURN r;
        END;
        $$ LANGUAGE plpgsql;
        """,
        "DROP TRIGGER IF EXISTS tr_audit_vehiculo ON vehiculo;",
        """
        CREATE TRIGGER tr_audit_vehiculo
        AFTER INSERT OR UPDATE OR DELETE
        ON vehiculo
        FOR EACH ROW
        EXECUTE FUNCTION fn_audit_vehiculo();
        """,
        # --- auditoría de usuarios y permisos ---
        """
        CREATE OR REPLACE FUNCTION fn_audit_usuario()
        RETURNS TRIGGER AS $$
        DECLARE
            r RECORD;
            anterior JSONB;
            nuevo JSONB;
        BEGIN
            r := CASE WHEN (TG_OP = 'DELETE') THEN OLD ELSE NEW END;
            -- el hash de la contraseña no se copia nunca; solo se anota que ha cambiado
            anterior := CASE WHEN (TG_OP = 'INSERT') THEN NULL ELSE to_jsonb(OLD) - 'password_hash' END;
            nuevo := CASE WHEN (TG_OP = 'DELETE') THEN NULL ELSE to_jsonb(NEW) - 'password_hash' END;
            IF TG_OP = 'UPDATE' AND TG_TABLE_NAME = 'usuario'
               AND (to_jsonb(OLD) -> 'password_hash') IS DISTINCT FROM (to_jsonb(NEW) -> 'password_hash') THEN
                nuevo := nuevo || '{"password_cambiada": true}'::jsonb;
            END IF;

            INSERT INTO audit_usuario (operacion, stamp, user_id, tabla, usuario_id, datos_anteriores, datos_nuevos)
            VALUES (
                SUBSTR(TG_OP, 1, 1),
                now(),
                COALESCE(NULLIF(current_setting('app.usuario', true), ''), current_user),
                TG_TABLE_NAME,
                (to_jsonb(r) ->> CASE WHEN TG_TABLE_NAME = 'usuario' THEN 'id' ELSE 'usuario_id' END)::int,
                anterior,
                nuevo
            );
            RETURN r;
        END;
        $$ LANGUAGE plpgsql;
        """,
        "DROP TRIGGER IF EXISTS tr_audit_usuario ON usuario;",
        """
        CREATE TRIGGER tr_audit_usuario AFTER INSERT OR UPDATE OR DELETE ON usuario
        FOR EACH ROW EXECUTE FUNCTION fn_audit_usuario();
        """,
        "DROP TRIGGER IF EXISTS tr_audit_usuario_permiso ON usuario_permiso;",
        """
        CREATE TRIGGER tr_audit_usuario_permiso AFTER INSERT OR UPDATE OR DELETE ON usuario_permiso
        FOR EACH ROW EXECUTE FUNCTION fn_audit_usuario();
        """,
    ]

    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        for cmd in comandos:
            conn.execute(text(cmd))
    print("Triggers y tablas de auditoría creados correctamente.")


# ---------------------------------------------------------------- auditoría

def informacion_audit(limite=200):
    session = Session()
    try:
        return (session.query(AuditVehiculo)
                       .order_by(AuditVehiculo.stamp.desc(), AuditVehiculo.id.desc())
                       .limit(limite).all())
    finally:
        session.close()


def informacion_audit_usuarios(limite=200):
    session = Session()
    try:
        return (session.query(AuditUsuario)
                       .order_by(AuditUsuario.stamp.desc(), AuditUsuario.id.desc())
                       .limit(limite).all())
    finally:
        session.close()


def registrar_acceso(email, evento, ip=None):
    session = Session()
    try:
        session.add(RegistroAcceso(email=email, evento=evento, ip=ip))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def accesos_recientes(limite=200):
    session = Session()
    try:
        return (session.query(RegistroAcceso)
                       .order_by(RegistroAcceso.stamp.desc(), RegistroAcceso.id.desc())
                       .limit(limite).all())
    finally:
        session.close()


def intentos_fallidos(email, minutos=15):
    """Inicios de sesión fallidos de ese email desde hace `minutos` (se reinician al acertar)."""
    desde = datetime.now() - timedelta(minutes=minutos)
    session = Session()
    try:
        ultimo_ok = (session.query(func.max(RegistroAcceso.stamp))
                            .filter(RegistroAcceso.email == email,
                                    RegistroAcceso.evento == "login_ok").scalar())
        desde = max(desde, ultimo_ok) if ultimo_ok else desde
        return (session.query(RegistroAcceso)
                       .filter(RegistroAcceso.email == email,
                               RegistroAcceso.evento == "login_fallido",
                               RegistroAcceso.stamp >= desde).count())
    finally:
        session.close()


# ----------------------------------------------------------------- usuarios

def usuario_por_id(id):
    session = Session()
    try:
        return session.query(Usuario).filter(Usuario.id == id).first()
    finally:
        session.close()


def usuario_por_email(email):
    session = Session()
    try:
        return session.query(Usuario).filter(Usuario.email == email.strip().lower()).first()
    finally:
        session.close()


def listar_usuarios():
    session = Session()
    try:
        return session.query(Usuario).order_by(Usuario.rol, Usuario.email).all()
    finally:
        session.close()


def _validar_permisos(permisos):
    desconocidos = set(permisos) - set(PERMISOS)
    if desconocidos:
        raise ValueError("Permiso no válido.")


def crear_usuario(email, nombre, rol, permisos, password_hash, debe_cambiar=True):
    """Crea un usuario. Por defecto con contraseña temporal: debe cambiarla en el primer acceso."""
    _validar_permisos(permisos)
    session = Session()
    try:
        usuario = Usuario(email=email.strip().lower(), nombre=nombre.strip(), rol=rol,
                          password_hash=password_hash, activo=True, debe_cambiar_password=debe_cambiar)
        # el admin lo puede todo; guardar permisos sueltos solo tiene sentido en empleados
        if rol != "admin":
            usuario.permisos = [UsuarioPermiso(permiso=p) for p in sorted(set(permisos))]
        session.add(usuario)
        session.commit()
        return usuario.id
    except IntegrityError as e:
        session.rollback()
        raise EmailDuplicado(email) from e
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _admins_activos(session, excluyendo_id=None):
    q = session.query(Usuario).filter(Usuario.rol == "admin", Usuario.activo.is_(True))
    if excluyendo_id is not None:
        q = q.filter(Usuario.id != excluyendo_id)
    return q.count()


def actualizar_usuario(id, nombre, rol, activo, permisos, actor_id=None):
    """Modifica nombre, rol, estado y permisos. Devuelve False si no existe.
    Reglas: no se puede dejar el sistema sin administradores activos ni desactivarse
    o quitarse el rol de administrador a uno mismo."""
    _validar_permisos(permisos)
    session = Session()
    try:
        usuario = session.query(Usuario).filter(Usuario.id == id).first()
        if usuario is None:
            return False
        deja_de_ser_admin_activo = usuario.rol == "admin" and usuario.activo and (rol != "admin" or not activo)
        if deja_de_ser_admin_activo:
            if actor_id is not None and usuario.id == actor_id:
                raise ValueError("No puedes quitarte el rol de administrador ni desactivar tu propia cuenta.")
            if _admins_activos(session, excluyendo_id=usuario.id) == 0:
                raise ValueError("Debe quedar al menos un administrador activo.")

        usuario.nombre = nombre.strip()
        usuario.rol = rol
        usuario.activo = activo
        nuevos = set() if rol == "admin" else set(permisos)
        actuales = {p.permiso: p for p in usuario.permisos}
        for codigo, fila in actuales.items():
            if codigo not in nuevos:
                usuario.permisos.remove(fila)
        for codigo in sorted(nuevos - set(actuales)):
            usuario.permisos.append(UsuarioPermiso(permiso=codigo))
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def cambiar_password(id, password_hash, debe_cambiar):
    session = Session()
    try:
        usuario = session.query(Usuario).filter(Usuario.id == id).first()
        if usuario is None:
            return False
        usuario.password_hash = password_hash
        usuario.debe_cambiar_password = debe_cambiar
        session.commit()
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ------------------------------------------------------------------ resumen

# El CSV importado trae precios NaN; se excluyen para no falsear sumas ni medias.
_PRECIOS_OK = "precio_compra <> 'NaN' AND precio_venta <> 'NaN'"


def resumen_economico():
    """Cifras agregadas del negocio. Todo lo económico, sin datos de vehículos concretos."""
    with engine.connect() as conn:
        def una(sql):
            return conn.execute(text(sql)).mappings().first()

        def varias(sql):
            return [dict(f) for f in conn.execute(text(sql)).mappings()]

        stock = una(f"""
            SELECT count(*) AS unidades,
                   COALESCE(sum(precio_compra), 0) AS coste,
                   COALESCE(sum(precio_venta), 0) AS valor_venta
            FROM vehiculo WHERE estado <> 'V' AND {_PRECIOS_OK}""")
        vendidos = una(f"""
            SELECT count(*) AS unidades,
                   COALESCE(sum(COALESCE(precio_final, precio_venta)), 0) AS ingresos,
                   COALESCE(sum(precio_compra), 0) AS coste,
                   COALESCE(sum(COALESCE(precio_final, precio_venta) - precio_compra), 0) AS margen,
                   avg(COALESCE(precio_final, precio_venta) - precio_compra) AS margen_medio,
                   avg(EXTRACT(EPOCH FROM (fecha_venta - fecha_entrada)) / 86400) AS dias_en_stock
            FROM vehiculo WHERE estado = 'V' AND {_PRECIOS_OK}""")
        sin_precio = una("""SELECT count(*) AS n FROM vehiculo
                            WHERE precio_compra = 'NaN' OR precio_venta = 'NaN'""")["n"]
        compras = varias(f"""
            SELECT to_char(date_trunc('month', fecha_entrada), 'YYYY-MM') AS mes,
                   count(*) AS unidades, sum(precio_compra) AS importe
            FROM vehiculo WHERE {_PRECIOS_OK}
            GROUP BY 1 ORDER BY 1 DESC LIMIT 12""")
        ventas = varias(f"""
            SELECT to_char(date_trunc('month', fecha_venta), 'YYYY-MM') AS mes,
                   count(*) AS unidades,
                   sum(COALESCE(precio_final, precio_venta)) AS importe,
                   sum(COALESCE(precio_final, precio_venta) - precio_compra) AS margen
            FROM vehiculo WHERE estado = 'V' AND fecha_venta IS NOT NULL AND {_PRECIOS_OK}
            GROUP BY 1 ORDER BY 1 DESC LIMIT 12""")
        por_marca = varias(f"""
            SELECT marca, count(*) AS unidades,
                   sum(COALESCE(precio_final, precio_venta) - precio_compra) AS margen
            FROM vehiculo WHERE estado = 'V' AND {_PRECIOS_OK}
            GROUP BY marca ORDER BY margen DESC LIMIT 10""")
    return {"stock": dict(stock), "vendidos": dict(vendidos), "sin_precio": sin_precio,
            "compras": compras, "ventas": ventas, "por_marca": por_marca}
