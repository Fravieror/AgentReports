import pandas as pd
from datetime import datetime
from config import PRICE_PER_GALLON_COP_GASOLINE, PRICE_PER_GGE_COP_NATURAL_GAS, MAINTENANCE_SCHEDULE, DEVICE_TYPE_MAP
from maintenance import get_last_maintenance, update_maintenance


def process_data(devi, distance, top_speed, odometer, engine_hours, alerts_email_body):
    """Evaluate metrics and append human-readable alert strings to alerts_email_body.

    Returns the modified alerts_email_body.
    """
    # --- ENGINE HOURS ALERT ---
    if engine_hours and engine_hours > 0:
        avg_speed = distance / engine_hours if engine_hours else 0
        if avg_speed < 10:
            alerts_email_body.append(
                f"⚠️ Posible uso ineficiente - {devi}\n"
                f"Distancia: {distance:.1f} km, Horas de motor: {engine_hours:.1f} h\n"
                f"Velocidad promedio: {avg_speed:.1f} km/h (muy baja para zona rural)\n"
            )

    # --- SPEED CHECK ---
    if top_speed and top_speed > 80:
        alerts_email_body.append(
            f"⚠️ Límite de velocidad excedido - {devi}\n"
            f"Velocidad máxima: {top_speed} km/h\n"
        )

    # --- DISTANCE CHECK ---
    if distance and distance > 150:
        alerts_email_body.append(
            f"⚠️ Distancia excesiva - {devi}\n"
            f"Distancia: {distance} km\n"
        )

    # --- MAINTENANCE CHECK ---
    maintenance_due = []
    vehicle_type = DEVICE_TYPE_MAP.get(devi)
    if vehicle_type:
        for component, interval in MAINTENANCE_SCHEDULE[vehicle_type].items():
            last_maint = get_last_maintenance(devi, component)
            if last_maint is None or (odometer - last_maint) >= interval:
                maintenance_due.append(f"🔧 {component} (cada {interval:,} km) - ¡Revisar!")
                update_maintenance(devi, component, odometer)

    if maintenance_due:
        alerts_email_body.append("🚗 *Mantenimientos requeridos:*\n" + "\n".join(maintenance_due) + "\n")

    return alerts_email_body
