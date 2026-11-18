# Gestión de Concesionario

Aplicación web para gestionar el inventario de un concesionario de coches de ocasión. Permite dar de alta, consultar, modificar y borrar vehículos, y guarda un historial de auditoría de todos los cambios.

Es un proyecto personal para practicar con Flask, SQLAlchemy y PostgreSQL.

## Qué hace

- Listado de vehículos paginado (20 por página).
- Búsqueda por marca, modelo o VIN, filtros por estado, tipo de motor, rango de precio y kilómetros máximos, y ordenación por varios campos. Los filtros se mantienen al cambiar de página.
- Ficha de detalle de cada vehículo.
- Inicio de sesión con email y contraseña. No hay registro público: las cuentas las crea un administrador.
- Dos roles, administrador y empleado, y permisos sueltos por empleado (mínimo privilegio, ver más abajo).
- Panel de administración de usuarios: alta con contraseña temporal, edición de rol y permisos, desactivación y reseteo de contraseña.
- Resumen económico: valor del stock, margen medio, compras y ventas por mes y margen por marca.
- Protección CSRF en todos los formularios y bloqueo temporal tras 5 intentos de login fallidos.
- Alta, modificación y baja de vehículos. La baja pide confirmación.
- Mensajes al usuario cuando algo falla (VIN duplicado, campo inválido, número mal escrito). El formulario conserva lo que se había escrito.
- Auditoría automática: un trigger de PostgreSQL guarda cada `INSERT`, `UPDATE` y `DELETE` sobre la tabla de vehículos, con el email del usuario de la aplicación que lo hizo y el estado anterior en los cambios. Se consulta en `/vehiculos/auditoria`.
- Auditoría de usuarios: otro trigger registra los cambios en cuentas y permisos (nunca el hash de la contraseña), y una tabla aparte guarda los accesos. Se consulta en `/admin/historial`.
- Validación en el modelo: año entre 1900 y 2100, y tipo de motor y estado restringidos a valores válidos.
- Importación masiva de unos 7.000 vehículos desde un CSV, generando VINs válidos con dígito de control.
- Páginas de error 404 y 500 personalizadas.

## Tecnologías

| Capa | Herramienta |
|---|---|
| Backend | Python 3.12, Flask 3 |
| Base de datos | PostgreSQL, SQLAlchemy 2, psycopg2 |
| Datos | pandas (importación del CSV) |
| Sesiones y seguridad | Flask-Login, Flask-WTF (CSRF), hashes de contraseña de Werkzeug |
| Frontend | Plantillas Jinja2, Bootstrap 5 y CSS propio |

## Requisitos

- Python 3.12 o superior
- Un servidor PostgreSQL con una base de datos vacía para el proyecto
- Git

## Instalación

```bash
git clone https://github.com/FerMelero/gestion-concesionario.git
cd gestion-concesionario

python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Configuración (`.env`)

Hay que crear un archivo `.env` en la raíz del proyecto. Está en `.gitignore`, así que no se sube al repositorio.

```env
user=mi_usuario
password=mi_contraseña
host=localhost
port=5432
dbname=concesionario
VIN_GENERATOR_PATH=/ruta/absoluta/a/gestion-concesionario/VinGenerator
SECRET_KEY=una_cadena_larga_y_aleatoria
SESSION_COOKIE_SECURE=1   # solo en producción con HTTPS
```

| Variable | Descripción |
|---|---|
| `user`, `password` | Credenciales de PostgreSQL |
| `host`, `port` | Dirección del servidor |
| `dbname` | Nombre de la base de datos |
| `VIN_GENERATOR_PATH` | Ruta absoluta a la carpeta `VinGenerator` de este repo. La usa la importación del CSV para generar los VIN |
| `SECRET_KEY` | Clave con la que Flask firma la sesión y el token CSRF. Si no se define, se usa una de desarrollo, que no sirve para producción |
| `SESSION_COOKIE_SECURE` | Poner `1` cuando la aplicación se sirva por HTTPS, para que la cookie de sesión no viaje sin cifrar |

### Preparar la base de datos

Desde la raíz del proyecto y en este orden:

```bash
# 1. Crear las tablas e importar el CSV
#    Ojo: borra y recrea las tablas de vehículos (no toca usuarios ni accesos). Solo para bases de desarrollo.
python dataset.py

# 2. Crear usuarios, permisos, columnas nuevas y los triggers de auditoría
flask --app app migrar

# 3. Crear la primera cuenta de administrador (pide nombre y contraseña)
flask --app app crear-admin tu@email.com
```

`migrar` se puede lanzar las veces que haga falta y no borra datos. También sirve para actualizar una base de datos creada con una versión anterior del proyecto.

El trigger se crea después de la importación a propósito. Así los 7.000 vehículos importados no llenan el historial de auditoría con inserciones masivas.

Si se prefiere empezar con un solo coche de prueba en vez del CSV:

```bash
flask --app app migrar
python -m models.insert_demo_data
flask --app app crear-admin tu@email.com
```

## Ejecutar la aplicación

```bash
flask --app app run --debug
```

Después abrir <http://127.0.0.1:5000> en el navegador.

## Usuarios y permisos

Hay dos roles. El administrador puede todo, incluida la gestión de usuarios. Al empleado se le conceden permisos sueltos, y todos los empleados pueden consultar el inventario.

| Permiso | Qué permite |
|---|---|
| `vehiculos.crear` | Dar de alta vehículos |
| `vehiculos.editar` | Modificar vehículos |
| `vehiculos.eliminar` | Eliminar vehículos |
| `costes.ver` | Ver el precio de compra y el margen |
| `resumen.ver` | Ver el resumen económico |
| `auditoria.ver` | Ver el registro de auditoría de vehículos |

Un empleado nuevo nace con crear, editar y eliminar, y el administrador puede quitar cualquiera. La gestión de usuarios no es un permiso que se pueda conceder: es exclusiva del rol administrador.

- Las cuentas nuevas y las reseteadas tienen una contraseña temporal que se muestra una sola vez. La persona debe cambiarla en su primer acceso.
- Las cuentas no se borran, se desactivan, para conservar el historial.
- No se puede dejar el sistema sin administradores activos, ni quitarse uno el rol a sí mismo.
- Sin `costes.ver` no se ve el precio de compra ni el margen en ninguna pantalla. Al editar un vehículo, ese campo no se toca.
- Tras 5 intentos fallidos seguidos, el email queda bloqueado 15 minutos.

## Rutas

| Ruta | Permiso | Descripción |
|---|---|---|
| `/login`, `/logout` | | Inicio y cierre de sesión (el cierre es por POST) |
| `/cuenta/password` | sesión | Cambio de la propia contraseña |
| `/` | sesión | Listado. Admite `page`, `q`, `estado`, `motor`, `precio_min`, `precio_max`, `km_max`, `orden` y `direccion` |
| `/vehiculos/<id>` | sesión | Ficha del vehículo |
| `/nuevo` | `vehiculos.crear` | Alta de vehículo |
| `/vehiculos/modificar/<id>` | `vehiculos.editar` | Edición del vehículo |
| `/vehiculos/eliminar/<id>` | `vehiculos.eliminar` | Confirmación y borrado |
| `/resumen` | `resumen.ver` | Resumen económico |
| `/vehiculos/auditoria` | `auditoria.ver` | Últimos 200 cambios en vehículos |
| `/admin/usuarios` y subrutas | administrador | Alta, edición y reseteo de contraseñas |
| `/admin/historial` | administrador | Cambios en cuentas y accesos |

Ejemplo: `/?q=audi&estado=D&precio_max=15000&orden=precio&direccion=desc` lista los Audi disponibles de menos de 15.000 €, del más caro al más barato.

## Tests

Los tests usan una base de datos aparte para no tocar la de desarrollo. Hay que crearla una vez (el nombre debe terminar en `_test`) y lanzar pytest:

```bash
psql -U mi_usuario -d postgres -c "CREATE DATABASE concesionario_test"
python -m pytest tests
```

Si se quiere otro nombre, se indica con la variable de entorno `TEST_DBNAME`. Cubren el login, los permisos, el panel de administración, el CSRF y la auditoría con el usuario real. El archivo `VinGenerator/tests.py` es del generador original y está escrito para Python 2, así que no funciona tal cual.

## Estructura

```
gestion-concesionario/
├── app.py                  # Factory de la aplicación Flask y manejadores de error
├── config.py               # Carga del .env y creación del engine de SQLAlchemy
├── dataset.py              # Importación masiva del CSV a la base de datos
├── used_cars_data.csv      # Dataset de origen
├── models/
│   ├── entities.py         # Modelos SQLAlchemy y catálogos (motores, estados, permisos)
│   ├── db.py               # Consultas, filtros, usuarios, resumen y triggers de auditoría
│   └── insert_demo_data.py # Inserta un vehículo de prueba
├── routes/
│   ├── vehicles.py         # Rutas de vehículos y lectura de formularios
│   ├── auth.py             # Login, logout y cambio de contraseña
│   └── admin.py            # Panel de administración de usuarios
├── templates/              # Plantillas Jinja2 (y errors/ con el 404 y el 500)
├── static/css/             # Estilos
├── utils/
│   ├── seguridad.py        # Contraseñas, redirecciones seguras y decoradores de permisos
│   └── vin_helper.py       # Puente hacia el generador de VIN
├── tests/                  # Tests con pytest (base de datos aparte)
└── VinGenerator/           # Generador de VIN válidos (ver créditos)
```

## Modelo de datos

- `vehiculo`: marca, modelo, kilómetros, VIN (único), año, motor, cilindrada, consumo, marchas, transmisión, precios de compra y venta, fecha de entrada, estado y potencia.
  - Motor: `G` gasolina, `D` diésel, `HB` híbrido, `HE` híbrido enchufable, `E` eléctrico, `GNC` gas natural.
  - Estado: `D` disponible, `R` reservado, `T` en taller, `V` vendido.
  - Venta: `fecha_venta` y `precio_final`, que solo se rellenan cuando el vehículo está vendido.
- `usuario` y `usuario_permiso`: cuentas (email, hash de contraseña, rol, activa) y permisos concedidos a cada empleado.
- `audit_usuario`: historial de cambios en usuarios y permisos, rellenado por trigger.
- `registro_acceso`: inicios y cierres de sesión, intentos fallidos y consultas de las páginas sensibles.
- `detalle_electrico`: batería y carga de los eléctricos (relación 1:1 con vehículo). Todavía no se usa desde la interfaz.
- `atributo` y `vehiculo_equipamiento`: catálogo de extras y tabla puente con el equipamiento de cada coche. Tampoco se usan todavía.
- `audit_vehiculo`: historial de operaciones sobre vehículos, rellenado por el trigger `tr_audit_vehiculo`. Guarda el email del usuario y, en modificaciones y borrados, el estado anterior.

## Pendiente

- [ ] CI/CD con GitHub Actions (ejecutar los tests en cada push y pull request; necesitará un PostgreSQL en el workflow)
- [ ] Portar a Python 3 los tests del generador de VIN
- [ ] Filtros y paginación en las páginas de auditoría y de historial
- [ ] Tabla de empleados y script que cree las cuentas de quienes aún no tengan
- [ ] Impedir a nivel de base de datos que la aplicación modifique o borre las tablas de auditoría
- [ ] Gestionar desde la interfaz los datos de los eléctricos y el equipamiento
- [ ] Limpiar los precios vacíos (NaN) que trae el CSV importado; mientras tanto el resumen los excluye

## Créditos

- El generador de VIN de [`VinGenerator/`](VinGenerator/) conserva su propia licencia ([LICENSE](VinGenerator/LICENSE)).
- El dataset de coches de ocasión (`used_cars_data.csv`) es de origen público.

## Autor

Fernando Melero ([@FerMelero](https://github.com/FerMelero))
