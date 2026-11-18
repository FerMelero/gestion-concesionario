# Gestión de Concesionario

Aplicación web para gestionar el inventario de un concesionario de coches de ocasión. Permite dar de alta, consultar, modificar y borrar vehículos, y guarda un historial de auditoría de todos los cambios.

Es un proyecto personal para practicar con Flask, SQLAlchemy y PostgreSQL.

## Qué hace

- Listado de vehículos paginado (20 por página).
- Búsqueda por marca, modelo o VIN, filtros por estado, tipo de motor, rango de precio y kilómetros máximos, y ordenación por varios campos. Los filtros se mantienen al cambiar de página.
- Ficha de detalle de cada vehículo.
- Alta, modificación y baja de vehículos. La baja pide confirmación.
- Mensajes al usuario cuando algo falla (VIN duplicado, campo inválido, número mal escrito). El formulario conserva lo que se había escrito.
- Auditoría automática: un trigger de PostgreSQL guarda cada `INSERT`, `UPDATE` y `DELETE` sobre la tabla de vehículos. Se consulta en `/vehiculos/auditoria`.
- Validación en el modelo: año entre 1900 y 2100, y tipo de motor y estado restringidos a valores válidos.
- Importación masiva de unos 7.000 vehículos desde un CSV, generando VINs válidos con dígito de control.
- Páginas de error 404 y 500 personalizadas.

## Tecnologías

| Capa | Herramienta |
|---|---|
| Backend | Python 3.12, Flask 3 |
| Base de datos | PostgreSQL, SQLAlchemy 2, psycopg2 |
| Datos | pandas (importación del CSV) |
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
```

| Variable | Descripción |
|---|---|
| `user`, `password` | Credenciales de PostgreSQL |
| `host`, `port` | Dirección del servidor |
| `dbname` | Nombre de la base de datos |
| `VIN_GENERATOR_PATH` | Ruta absoluta a la carpeta `VinGenerator` de este repo. La usa la importación del CSV para generar los VIN |
| `SECRET_KEY` | Clave de Flask para los mensajes al usuario. Si no se define, se usa una de desarrollo, que no sirve para producción |

### Preparar la base de datos

Desde la raíz del proyecto y en este orden:

```bash
# 1. Crear las tablas e importar el CSV
#    Ojo: borra y recrea todas las tablas (drop_all). Solo para bases de datos de desarrollo.
python dataset.py

# 2. Crear la tabla de auditoría y el trigger
python -c "from models.db import crear_audits; crear_audits()"
```

El trigger se crea después de la importación a propósito. Así los 7.000 vehículos importados no llenan el historial de auditoría con inserciones masivas.

Si se prefiere empezar con un solo coche de prueba en vez del CSV:

```bash
python -c "from models.db import crear_tablas, crear_audits; crear_tablas(); crear_audits()"
python -m models.insert_demo_data
```

## Ejecutar la aplicación

```bash
flask --app app run --debug
```

Después abrir <http://127.0.0.1:5000> en el navegador.

## Rutas

| Ruta | Método | Descripción |
|---|---|---|
| `/` | GET | Listado. Admite `page`, `q`, `estado`, `motor`, `precio_min`, `precio_max`, `km_max`, `orden` y `direccion` |
| `/nuevo` | GET, POST | Alta de vehículo |
| `/vehiculos/<id>` | GET | Ficha del vehículo |
| `/vehiculos/modificar/<id>` | GET, POST | Edición del vehículo |
| `/vehiculos/eliminar/<id>` | GET, POST | Confirmación y borrado |
| `/vehiculos/auditoria` | GET | Últimos 200 cambios registrados |

Ejemplo: `/?q=audi&estado=D&precio_max=15000&orden=precio&direccion=desc` lista los Audi disponibles de menos de 15.000 €, del más caro al más barato.

## Tests

Todavía no hay tests propios del proyecto. El archivo `VinGenerator/tests.py` es del generador original y está escrito para Python 2, así que no funciona tal cual.

## Estructura

```
gestion-concesionario/
├── app.py                  # Factory de la aplicación Flask y manejadores de error
├── config.py               # Carga del .env y creación del engine de SQLAlchemy
├── dataset.py              # Importación masiva del CSV a la base de datos
├── used_cars_data.csv      # Dataset de origen
├── models/
│   ├── entities.py         # Modelos SQLAlchemy y catálogos de motores y estados
│   ├── db.py               # Consultas, filtros, CRUD y creación del trigger de auditoría
│   └── insert_demo_data.py # Inserta un vehículo de prueba
├── routes/
│   └── vehicles.py         # Rutas de vehículos y lectura de formularios
├── templates/              # Plantillas Jinja2 (y errors/ con el 404 y el 500)
├── static/css/             # Estilos
├── utils/
│   └── vin_helper.py       # Puente hacia el generador de VIN
└── VinGenerator/           # Generador de VIN válidos (ver créditos)
```

## Modelo de datos

- `vehiculo`: marca, modelo, kilómetros, VIN (único), año, motor, cilindrada, consumo, marchas, transmisión, precios de compra y venta, fecha de entrada, estado y potencia.
  - Motor: `G` gasolina, `D` diésel, `HB` híbrido, `HE` híbrido enchufable, `E` eléctrico, `GNC` gas natural.
  - Estado: `D` disponible, `R` reservado, `T` en taller, `V` vendido.
- `detalle_electrico`: batería y carga de los eléctricos (relación 1:1 con vehículo). Todavía no se usa desde la interfaz.
- `atributo` y `vehiculo_equipamiento`: catálogo de extras y tabla puente con el equipamiento de cada coche. Tampoco se usan todavía.
- `audit_vehiculo`: historial de operaciones, rellenado por el trigger `tr_audit_vehiculo`.

## Pendiente

- [ ] CI/CD con GitHub Actions (ejecutar los tests en cada push y pull request)
- [ ] Tests de las rutas y de las validaciones del modelo, y portar los del generador de VIN a Python 3
- [ ] Autenticación de usuarios y protección CSRF
- [ ] Que la auditoría guarde el usuario de la aplicación y no el de PostgreSQL
- [ ] Paginación y filtros en la página de auditoría
- [ ] Gestionar desde la interfaz los datos de los eléctricos y el equipamiento
- [ ] Limpiar los precios vacíos (NaN) que trae el CSV importado

## Créditos

- El generador de VIN de [`VinGenerator/`](VinGenerator/) conserva su propia licencia ([LICENSE](VinGenerator/LICENSE)).
- El dataset de coches de ocasión (`used_cars_data.csv`) es de origen público.

## Autor

Fernando Melero ([@FerMelero](https://github.com/FerMelero))
