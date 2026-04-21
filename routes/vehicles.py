from flask import Blueprint, render_template, request, redirect, url_for
from models.db import get_all_vehicles, insert_vehicle, vehicle_by_id, delete_vehicle, mod_vehiculo
from datetime import datetime

vehiculos_bp = Blueprint('vehiculos', __name__)

# ruta por defecto, se ve una lista de los vehiculos disponibles
@vehiculos_bp.route('/')
def index():
    lista = get_all_vehicles()
    return render_template('index.html', vehiculos=lista)


# ruta para añadir nuevos vehiculos, de momento solo rellenamos ciertas cosas
@vehiculos_bp.route("/nuevo", methods=["GET", "POST"])
def new_vehicle():
    if request.method == "POST":
        marca = request.form["marca"]
        modelo = request.form["modelo"]
        kilometros = float(request.form["kilometros"])
        vin = request.form["vin"]
        
        anio = datetime.strptime(request.form["anio"], '%Y-%m-%d')
        f_entrada = datetime.strptime(request.form["fEntrada"], '%Y-%m-%d')
        
        motor = request.form["motor"]
        potencia = int(request.form["potencia"])
        p_compra = float(request.form["pCompra"])
        p_venta = float(request.form["pVenta"])
        estado = request.form["estado"]

        insert_vehicle(marca, modelo, kilometros, vin, anio, motor, potencia, p_compra, p_venta, estado, f_entrada)

        return redirect(url_for('vehiculos.index'))
    
    return render_template('newVehicle.html')

# eliminar un vehiculo dado un id (se accede con el boton de inicio)
@vehiculos_bp.route('/vehiculos/eliminar/<int:id>', methods=["GET", "POST"])
def eliminar_vehiculo(id):
    vehiculo_objeto = vehicle_by_id(id)
    if request.method == "POST":
        delete_vehicle(vehiculo_objeto.id)
        return redirect(url_for('vehiculos.index'))
        
    return render_template('deleteConfirm.html', vehiculo = vehiculo_objeto)


# obtener la información relativa a un vehículo específico
@vehiculos_bp.route('/vehiculos/<int:id>')
def vehiculo_id(id):
    id_vehiculo = vehicle_by_id(id)

    return render_template('vehicleId.html', vehiculo=id_vehiculo)

@vehiculos_bp.route('/vehiculos/modificar/<int:id>', methods=["GET", "POST"])
def modificar_vehiculo(id):
    vehiculo_objeto = vehicle_by_id(id)
    if request.method == "POST":
        registro = {
        "marca" : request.form["marca"],
        "modelo" :request.form["modelo"],
        "kilometros" : float(request.form["kilometros"]),
        
        "anio" : datetime.strptime(request.form["anio"], '%Y-%m-%d'),
        "fecha_entrada" : datetime.strptime(request.form["fEntrada"], '%Y-%m-%d'),
        
        "motor" : request.form["motor"],
        "cilindrada" : request.form["cilindrada"],
        "consumo": float(request.form["consumo"]),
        "potencia" : int(request.form["potencia"]),
        "transmision" : request.form["transmision"],
        "marchas" : request.form["marchas"],
        "precio_compra" : float(request.form["pCompra"]),
        "precio_venta" : float(request.form["pVenta"]),
        "estado" : request.form["estado"]
        }
        mod_vehiculo(id, registro)
        return redirect(url_for('vehiculos.vehiculo_id', id=id))

    return render_template('modifyVehicle.html', vehiculo=vehiculo_objeto)