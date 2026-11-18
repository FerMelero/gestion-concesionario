from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from models.db import (VinDuplicado, delete_vehicle, get_all_vehicles, informacion_audit,
                       insert_vehicle, mod_vehiculo, vehicle_by_id)
from models.entities import ESTADOS, MOTORES

vehiculos_bp = Blueprint('vehiculos', __name__)

PER_PAGE = 20


@vehiculos_bp.app_context_processor
def catalogos():
    # disponibles en todas las plantillas para pintar selects y etiquetas
    return {"MOTORES": MOTORES, "ESTADOS": ESTADOS}


def _numero(valor, tipo, etiqueta, obligatorio=False):
    """Convierte un campo de formulario. Vacío -> None si es opcional."""
    valor = (valor or "").strip()
    if not valor:
        if obligatorio:
            raise ValueError(f"El campo «{etiqueta}» es obligatorio.")
        return None
    try:
        return tipo(valor)
    except ValueError:
        raise ValueError(f"El campo «{etiqueta}» no es un número válido.") from None


def _fecha(valor, etiqueta):
    try:
        return datetime.strptime(valor, '%Y-%m-%d')
    except (TypeError, ValueError):
        raise ValueError(f"El campo «{etiqueta}» no es una fecha válida.") from None


def _leer_formulario(form, con_vin):
    """Lee y convierte el formulario de alta/edición. Lanza ValueError con un
    mensaje legible si algún campo no es correcto."""
    datos = {
        "marca": form.get("marca", "").strip(),
        "modelo": form.get("modelo", "").strip(),
        "kilometros": _numero(form.get("kilometros"), float, "Kilómetros", True),
        "anio": _fecha(form.get("anio"), "Año de fabricación"),
        "fecha_entrada": _fecha(form.get("fEntrada"), "Fecha de entrada"),
        "motor": form.get("motor", ""),
        "cilindrada": _numero(form.get("cilindrada"), int, "Cilindrada"),
        "consumo": _numero(form.get("consumo"), float, "Consumo", True),
        "potencia": _numero(form.get("potencia"), int, "Potencia", True),
        "transmision": form.get("transmision", "").strip() or None,
        "marchas": _numero(form.get("marchas"), int, "Marchas"),
        "precio_compra": _numero(form.get("pCompra"), float, "Precio de compra", True),
        "precio_venta": _numero(form.get("pVenta"), float, "Precio de venta", True),
        "estado": form.get("estado", ""),
    }
    if not datos["marca"] or not datos["modelo"]:
        raise ValueError("La marca y el modelo son obligatorios.")
    if datos["motor"] not in MOTORES:
        raise ValueError("Tipo de motor no válido.")
    if datos["estado"] not in ESTADOS:
        raise ValueError("Estado no válido.")
    if datos["kilometros"] < 0 or datos["precio_compra"] < 0 or datos["precio_venta"] < 0:
        raise ValueError("Los kilómetros y los precios no pueden ser negativos.")
    if con_vin:
        vin = form.get("vin", "").strip().upper()
        if len(vin) != 17:
            raise ValueError("El VIN debe tener 17 caracteres.")
        datos["vin"] = vin
    return datos


def _filtros_desde_url():
    """Lee los filtros del listado de la query string. Los valores no válidos se ignoran."""
    args = request.args

    def num(nombre):
        try:
            return float(args[nombre]) if args.get(nombre, "").strip() else None
        except ValueError:
            return None

    estado = args.get("estado", "")
    motor = args.get("motor", "")
    return {
        "q": args.get("q", "").strip(),
        "estado": estado if estado in ESTADOS else "",
        "motor": motor if motor in MOTORES else "",
        "precio_min": num("precio_min"),
        "precio_max": num("precio_max"),
        "km_max": num("km_max"),
        "orden": args.get("orden", "id"),
        "direccion": "desc" if args.get("direccion") == "desc" else "asc",
    }


# ruta por defecto: listado de vehículos con búsqueda, filtros y ordenación
@vehiculos_bp.route('/')
def index():
    page = max(1, request.args.get('page', 1, type=int))
    filtros = _filtros_desde_url()
    data = get_all_vehicles(page, PER_PAGE, filtros)

    # parámetros activos (sin la página) para conservarlos al paginar
    params = {k: v for k, v in filtros.items() if v not in ("", None)}
    if params.get("orden") == "id":
        params.pop("orden")
    if params.get("direccion") == "asc":
        params.pop("direccion")
    hay_filtros = any(filtros[k] not in ("", None)
                      for k in ("q", "estado", "motor", "precio_min", "precio_max", "km_max"))

    return render_template('index.html', vehiculos=data['items'], pagination=data,
                           filtros=filtros, params=params, hay_filtros=hay_filtros)


@vehiculos_bp.route("/nuevo", methods=["GET", "POST"])
def new_vehicle():
    if request.method == "POST":
        try:
            datos = _leer_formulario(request.form, con_vin=True)
            insert_vehicle(datos)
        except VinDuplicado:
            flash("Ya existe un vehículo con ese VIN.", "danger")
        except ValueError as e:
            flash(str(e), "danger")
        else:
            flash("Vehículo registrado correctamente.", "success")
            return redirect(url_for('vehiculos.index'))
        # algo ha fallado: se vuelve a mostrar el formulario con lo que se había escrito
        return render_template('newVehicle.html', form=request.form)

    return render_template('newVehicle.html', form={},
                           today_date=datetime.now().strftime('%Y-%m-%d'))


@vehiculos_bp.route('/vehiculos/eliminar/<int:id>', methods=["GET", "POST"])
def eliminar_vehiculo(id):
    vehiculo = vehicle_by_id(id)
    if vehiculo is None:
        abort(404)
    if request.method == "POST":
        if delete_vehicle(id):
            flash("Vehículo eliminado.", "success")
        return redirect(url_for('vehiculos.index'))

    return render_template('deleteConfirm.html', vehiculo=vehiculo)


@vehiculos_bp.route('/vehiculos/<int:id>')
def vehiculo_id(id):
    vehiculo = vehicle_by_id(id)
    if vehiculo is None:
        abort(404)
    return render_template('vehicleId.html', vehiculo=vehiculo)


@vehiculos_bp.route('/vehiculos/modificar/<int:id>', methods=["GET", "POST"])
def modificar_vehiculo(id):
    vehiculo = vehicle_by_id(id)
    if vehiculo is None:
        abort(404)

    if request.method == "POST":
        try:
            datos = _leer_formulario(request.form, con_vin=False)
            if not mod_vehiculo(id, datos):
                abort(404)
        except ValueError as e:
            flash(str(e), "danger")
            return render_template('modifyVehicle.html', vehiculo=vehiculo, form=request.form)
        flash("Cambios guardados.", "success")
        return redirect(url_for('vehiculos.vehiculo_id', id=id))

    return render_template('modifyVehicle.html', vehiculo=vehiculo, form={})


@vehiculos_bp.route('/vehiculos/auditoria')
def auditoria_vehiculos():
    return render_template('auditVehiculos.html', auditoria=informacion_audit())
