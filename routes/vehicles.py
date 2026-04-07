from flask import Blueprint, render_template, request, redirect, url_for
from models.db import get_all_vehicles, insert_vehicle, vehicle_by_id
from datetime import datetime

vehiculos_bp = Blueprint('vehiculos', __name__)

@vehiculos_bp.route('/')
def index():
    lista = get_all_vehicles()
    return render_template('index.html', vehiculos=lista)


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


@vehiculos_bp.route('/vehiculos/<int:id>')
def vehiculo_id(id):
    id_vehiculo = vehicle_by_id(id)

    return render_template('vehicleId.html', vehiculo=id_vehiculo)