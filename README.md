# 🚗 Gestión de Concesionario

Aplicación web para gestionar el inventario de un concesionario de vehículos de ocasión: alta, consulta, modificación y baja de coches, con un **historial de auditoría automático** de todos los cambios.

Proyecto personal hecho con **Flask**, **SQLAlchemy** y **PostgreSQL**.

[![CI](https://github.com/FerMelero/gestion-concesionario/actions/workflows/ci.yml/badge.svg)](https://github.com/FerMelero/gestion-concesionario/actions/workflows/ci.yml)

---

## ✨ Funcionalidades

- **Listado paginado** de vehículos (20 por página) en la página principal.
- **Ficha de detalle** de cada vehículo.
- **Alta, modificación y baja** de vehículos (la baja pide confirmación).
- **Auditoría automática**: un trigger de PostgreSQL registra cada `INSERT`, `UPDATE` y `DELETE` sobre la tabla de vehículos (quién, cuándo y qué datos), y se consulta desde `/vehiculos/auditoria`.
- **Validación en el modelo**: año entre 1900 y 2100, tipo de motor y estado de venta restringidos a valores válidos.
- **Importación masiva** de ~7.000 vehículos desde un CSV (`used_cars_data.csv`), generando VINs válidos con dígito de control.
- **Páginas de error** 404 y 500 personalizadas.
- **Integración continua** con GitHub Actions (ejecuta los tests en cada push y pull request).

## 🛠️ Tecnologías

| Capa | Herramienta |
|---|---|
| Backend | Python 3.12, Flask 3 |
| Base de datos | PostgreSQL, SQLAlchemy 2, psycopg2 |
| Datos | pandas (importación del CSV) |
| Frontend | Plantillas Jinja2 + CSS propio |
| Tests / CI | pytest, GitHub Actions |

## 📋 Requisitos previos

- Python 3.12 o superior
- Un servidor PostgreSQL accesible, con una base de datos vacía creada para el proyecto
- Git

## 🚀 Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/FerMelero/gestion-concesionario.git
cd gestion-concesionario

# 2. Crear y activar un entorno virtual
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate

# 3. Instalar las dependencias
pip install -r requirements.txt
```

### Configuración (`.env`)

Crea un archivo `.env` en la raíz del proyecto (está en `.gitignore`, no se sube al repositorio):

```env
user=mi_usuario
password=mi_contraseña
host=localhost
port=5432
dbname=concesionario
VIN_GENERATOR_PATH=/ruta/absoluta/a/gestion-concesionario/VinGenerator
```

| Variable | Descripción |
|---|---|
| `user`, `password` | Credenciales de PostgreSQL |
| `host`, `port` | Dirección del servidor (por defecto `localhost` y `5432`) |
| `dbname` | Nombre de la base de datos |
| `VIN_GENERATOR_PATH` | Ruta **absoluta** a la carpeta `VinGenerator` de este repo; la usa la importación del CSV para generar VINs |

### Preparar la base de datos

Ejecuta estos comandos **desde la raíz del proyecto y en este orden**:

```bash
# 1. Crear las tablas e importar el CSV con los vehículos
#    ⚠️ Borra y recrea todas las tablas (drop_all). Úsalo solo en una BD de desarrollo.
python dataset.py

# 2. Crear la tabla de auditoría y el trigger
python -c "from models.db import crear_audits; crear_audits()"
```

> El trigger se crea **después** de la importación a propósito: así los ~7.000 vehículos importados no llenan el historial de auditoría con inserciones masivas.

Si prefieres empezar con un único coche de prueba en lugar del CSV:

```bash
python -c "from models.db import crear_tablas, crear_audits; crear_tablas(); crear_audits()"
python -m models.insert_demo_data
```

## ▶️ Ejecutar la aplicación

```bash
flask --app app run --debug
```

Abre <http://127.0.0.1:5000> en el navegador.

## 🗺️ Rutas principales

| Ruta | Método | Descripción |
|---|---|---|
| `/` | GET | Listado paginado (`?page=2`) |
| `/nuevo` | GET, POST | Formulario de alta de vehículo |
| `/vehiculos/<id>` | GET | Ficha del vehículo |
| `/vehiculos/modificar/<id>` | GET, POST | Edición del vehículo |
| `/vehiculos/eliminar/<id>` | GET, POST | Confirmación y borrado |
| `/vehiculos/auditoria` | GET | Historial de cambios |

## 🧪 Tests

```bash
python -m pytest
```

Actualmente los tests cubren el generador de VIN (cálculo del dígito de control y formato del VIN generado). Los mismos tests se ejecutan automáticamente en GitHub Actions.

## 📁 Estructura del proyecto

```
gestion-concesionario/
├── app.py                  # Factory de la aplicación Flask y manejadores de error
├── config.py               # Carga del .env y creación del engine de SQLAlchemy
├── dataset.py              # Importación masiva del CSV a la base de datos
├── used_cars_data.csv      # Dataset de origen (coches de ocasión)
├── models/
│   ├── entities.py         # Modelos SQLAlchemy (Vehiculo, DetalleElectrico, AuditVehiculo...)
│   ├── db.py               # Consultas, CRUD y creación de triggers de auditoría
│   └── insert_demo_data.py # Inserta un vehículo de prueba
├── routes/
│   └── vehicles.py         # Blueprint con las rutas de vehículos
├── templates/              # Plantillas Jinja2 (+ errors/404 y 500)
├── static/css/             # Estilos
├── utils/
│   └── vin_helper.py       # Puente hacia el generador de VIN
├── VinGenerator/           # Generador de VIN válidos (ver créditos)
├── tests/                  # Tests con pytest
└── .github/workflows/      # Pipeline de CI
```

## 🗃️ Modelo de datos

- **`vehiculo`**: marca, modelo, kilómetros, VIN (único), año, motor (`D` diésel, `G` gasolina, `HB` híbrido, `E` eléctrico, `HE` híbrido enchufable, `GNC`), cilindrada, consumo, marchas, transmisión, precios de compra y venta, fecha de entrada, estado (`D` disponible, `R` reservado, `V` vendido) y potencia.
- **`detalle_electrico`**: datos de batería y carga para eléctricos (relación 1:1 con vehículo).
- **`atributo`** y **`vehiculo_equipamiento`**: catálogo de extras y tabla puente para el equipamiento variable de cada coche.
- **`audit_vehiculo`**: historial de operaciones, rellenado por el trigger `tr_audit_vehiculo`.

## 🔮 Próximos pasos

- [ ] Autenticación de usuarios y protección CSRF
- [ ] Manejo de errores y mensajes al usuario en los formularios
- [ ] Más tests (rutas y validaciones del modelo)
- [ ] Gestión desde la interfaz de los datos de vehículos eléctricos y del equipamiento
- [ ] Filtros y búsqueda en el listado

## 🙏 Créditos

- El generador de VIN de la carpeta [`VinGenerator/`](VinGenerator/) conserva su propia licencia ([LICENSE](VinGenerator/LICENSE)).
- Dataset de coches de ocasión (`used_cars_data.csv`) de origen público.

## 👤 Autor

**Fernando Melero** — [@FerMelero](https://github.com/FerMelero)
