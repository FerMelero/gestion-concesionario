from sqlalchemy import Column, Integer, BigInteger, String, ForeignKey, Boolean, Float, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, declarative_base, validates # validates añadido
from flask_login import UserMixin
from datetime import datetime

Base = declarative_base()

# Valores permitidos (código -> etiqueta). Se usan en el modelo, los formularios y las plantillas.
MOTORES = {
    "G": "Gasolina",
    "D": "Diésel",
    "HB": "Híbrido",
    "HE": "Híbrido enchufable",
    "E": "Eléctrico",
    "GNC": "Gas natural (GNC)",
}
# Permisos que el admin puede conceder a un empleado. "Ver vehículos" es la base de
# cualquier empleado y no se asigna; la gestión de usuarios es exclusiva del rol admin.
PERMISOS = {
    "vehiculos.crear": "Dar de alta vehículos",
    "vehiculos.editar": "Modificar vehículos",
    "vehiculos.eliminar": "Eliminar vehículos",
    "costes.ver": "Ver precio de compra y margen",
    "resumen.ver": "Ver el resumen económico",
    "auditoria.ver": "Ver el registro de auditoría de vehículos",
}
# Permisos con los que nace un empleado nuevo (el admin los puede quitar)
PERMISOS_EMPLEADO_POR_DEFECTO = ["vehiculos.crear", "vehiculos.editar", "vehiculos.eliminar"]
ROLES = {"admin": "Administrador", "empleado": "Empleado"}

ESTADOS = {
    "D": "Disponible",
    "R": "Reservado",
    "T": "En taller",
    "V": "Vendido",
}

class Vehiculo(Base):
    __tablename__ = "vehiculo"
    id = Column(Integer, primary_key=True, autoincrement=True)
    marca = Column(String(30), nullable=False)
    modelo = Column(String(80), nullable=False)
    kilometros = Column(Float, nullable=False)
    vin = Column(String(17), nullable=False, unique=True)
    anio = Column(DateTime, nullable=False)
    motor = Column(String(3), nullable=False)
    cilindrada = Column(Integer)
    consumo = Column(Float(6), nullable=False)
    marchas = Column(Integer)
    transmision = Column(String(12))
    precio_compra = Column(Float, nullable=False)
    precio_venta = Column(Float, nullable=False)
    fecha_entrada = Column(DateTime, nullable=False, default=datetime.now)
    estado = Column(String(1), nullable=False)
    potencia = Column(Integer, nullable=False)
    # solo se rellenan cuando el vehículo está vendido
    fecha_venta = Column(DateTime)
    precio_final = Column(Float)
    # falta equipamiento y si es eléctrico o híbrido enchufable velocidad de carga, KW, etc

    @validates('anio')
    def validate_anio(self, key, value):
        fecha_min = datetime(1900, 1, 1)
        fecha_max = datetime(2100, 12, 31)
        if not (fecha_min <= value <= fecha_max):
            raise ValueError(f"El año debe estar entre {fecha_min.year} y {fecha_max.year}")
        return value
    
    @validates('motor')
    def validate_motor(self, key, value): # Nombre único para que no se pisen
        if value not in MOTORES:
            raise ValueError("Motor no válido")
        return value
    
    @validates('estado')
    def validate_estado(self, key, value): # Nombre único para que no se pisen
        if value not in ESTADOS:
            raise ValueError("Estado no válido")
        return value

    # Relación 1 a 1 para datos eléctricos
    electrico_info = relationship("DetalleElectrico", back_populates="vehiculo", uselist=False)
    # usmos uselist=False para una relación 1:1
    
    # Relación para el equipamiento variable
    lista_equipamiento = relationship("VehiculoEquipamiento", back_populates="vehiculo")
    # aqui no ponemos uselist porque un coche puede tener mucho equipamiento

class DetalleElectrico(Base):
    __tablename__ = "detalle_electrico"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vehiculo_id = Column(Integer, ForeignKey('vehiculo.id'), unique=True)
    
    capacidad_bateria_kwh = Column(Float, nullable=False)
    velocidad_carga_kw = Column(Float, nullable=False)
    autonomia_wltp = Column(Integer, nullable=True)
    
    vehiculo = relationship("Vehiculo", back_populates="electrico_info")

class Atributo(Base):
    """Catálogo de extras: 'Techo Solar', 'Asientos Cuero', etc."""
    __tablename__ = "atributo"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), unique=True, nullable=False)
    
    vehiculos = relationship("VehiculoEquipamiento", back_populates="atributo")

class VehiculoEquipamiento(Base):
    """Tabla puente: une un vehículo concreto con sus extras"""
    __tablename__ = "vehiculo_equipamiento"
    id = Column(Integer, primary_key=True)
    vehiculo_id = Column(Integer, ForeignKey('vehiculo.id'))
    atributo_id = Column(Integer, ForeignKey('atributo.id'))
    valor = Column(String(50)) # Ejemplo: "Sí", "Panorámico", "Negro"
    
    vehiculo = relationship("Vehiculo", back_populates="lista_equipamiento")
    atributo = relationship("Atributo", back_populates="vehiculos")

class AuditVehiculo(Base):
    """Historial de cambios sobre vehículos. La rellena el trigger tr_audit_vehiculo.
    Guarda los valores resultantes de la operación (o los borrados, en un DELETE) y,
    en UPDATE y DELETE, el estado anterior completo en datos_anteriores."""
    __tablename__ = "audit_vehiculo"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    stamp = Column(DateTime, nullable=False, default=datetime.now)
    operacion = Column(String(1), nullable=False)
    user_id = Column(String(100), nullable=False)  # email del usuario de la aplicación

    id_vehiculo = Column(Integer)
    marca = Column(String(30))
    modelo = Column(String(80))
    kilometros = Column(Float)
    vin = Column(String(17))
    anio = Column(DateTime)
    motor = Column(String(3))
    cilindrada = Column(Integer)
    consumo = Column(Float)
    marchas = Column(Integer)
    transmision = Column(String(12))
    precio_compra = Column(Float)
    precio_venta = Column(Float)
    fecha_entrada = Column(DateTime)
    estado = Column(String(1))
    potencia = Column(Integer)
    fecha_venta = Column(DateTime)
    precio_final = Column(Float)
    datos_anteriores = Column(JSONB)

    ETIQUETAS = {
        "marca": "Marca", "modelo": "Modelo", "kilometros": "Km", "vin": "VIN", "anio": "Año",
        "motor": "Motor", "cilindrada": "Cilindrada", "consumo": "Consumo", "marchas": "Marchas",
        "transmision": "Transmisión", "precio_compra": "Precio compra", "precio_venta": "Precio venta",
        "fecha_entrada": "Fecha entrada", "estado": "Estado", "potencia": "Potencia",
        "fecha_venta": "Fecha venta", "precio_final": "Precio final",
    }

    def cambios(self, incluir_costes=True):
        """En un UPDATE, lista de (campo, antes, después) con lo que ha cambiado."""
        if self.operacion != "U" or not self.datos_anteriores:
            return []

        def normalizar(valor):
            if isinstance(valor, datetime):
                return valor.isoformat()
            return valor

        def legible(valor):
            if valor is None:
                return "-"
            if isinstance(valor, str) and len(valor) >= 10 and valor[4:5] == "-" and valor[10:11] == "T":
                return valor[:10] if valor.endswith("T00:00:00") else valor.replace("T", " ")
            return valor

        resultado = []
        for campo, etiqueta in self.ETIQUETAS.items():
            if campo == "precio_compra" and not incluir_costes:
                continue
            antes = self.datos_anteriores.get(campo)
            despues = normalizar(getattr(self, campo))
            if antes != despues:
                resultado.append((etiqueta, legible(antes), legible(despues)))
        return resultado


class Usuario(UserMixin, Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(120), nullable=False, unique=True)
    nombre = Column(String(80), nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(String(10), nullable=False, default="empleado")
    activo = Column(Boolean, nullable=False, default=True)
    # las cuentas nuevas y las reseteadas obligan a elegir contraseña propia
    debe_cambiar_password = Column(Boolean, nullable=False, default=True)
    creado = Column(DateTime, nullable=False, default=datetime.now)

    permisos = relationship("UsuarioPermiso", back_populates="usuario",
                            cascade="all, delete-orphan", lazy="joined")

    @validates('rol')
    def validate_rol(self, key, value):
        if value not in ROLES:
            raise ValueError("Rol no válido")
        return value

    @property
    def es_admin(self):
        return self.rol == "admin"

    @property
    def codigos_permisos(self):
        return {p.permiso for p in self.permisos}

    def tiene_permiso(self, permiso):
        """El admin lo puede todo. El empleado, solo lo que se le ha concedido."""
        return self.es_admin or permiso in self.codigos_permisos

    # Flask-Login: una cuenta desactivada no puede iniciar ni mantener sesión
    @property
    def is_active(self):
        return bool(self.activo)


class UsuarioPermiso(Base):
    __tablename__ = "usuario_permiso"

    usuario_id = Column(Integer, ForeignKey("usuario.id", ondelete="CASCADE"), primary_key=True)
    permiso = Column(String(40), primary_key=True)

    usuario = relationship("Usuario", back_populates="permisos")

    @validates('permiso')
    def validate_permiso(self, key, value):
        if value not in PERMISOS:
            raise ValueError("Permiso no válido")
        return value


class AuditUsuario(Base):
    """Historial de cambios en usuarios y permisos (trigger fn_audit_usuario).
    Nunca contiene el hash de la contraseña, solo si se ha cambiado."""
    __tablename__ = "audit_usuario"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    stamp = Column(DateTime, nullable=False, default=datetime.now)
    operacion = Column(String(1), nullable=False)
    user_id = Column(String(100), nullable=False)   # quién hizo el cambio
    tabla = Column(String(30), nullable=False)
    usuario_id = Column(Integer)                    # a quién afecta
    datos_anteriores = Column(JSONB)
    datos_nuevos = Column(JSONB)


class RegistroAcceso(Base):
    """Inicios de sesión (correctos y fallidos), cierres y accesos a páginas sensibles."""
    __tablename__ = "registro_acceso"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    stamp = Column(DateTime, nullable=False, default=datetime.now)
    email = Column(String(120))
    evento = Column(String(30), nullable=False)
    ip = Column(String(45))
