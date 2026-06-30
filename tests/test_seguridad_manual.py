"""Prueba rápida y manual de la lógica de detección de anomalías."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Permite importar desde src/modules sin instalar el paquete formalmente
sys.path.append(str(Path(__file__).parent.parent / "src"))

from modules.seguridad import evaluar_anomalia

# Caso 1: un pesquero normal, moviéndose despacio cerca de Vigo
pos_normal_1 = {"lat": 42.20, "lon": -8.80, "timestamp": datetime.now(timezone.utc)}
pos_normal_2 = {
    "lat": 42.205,
    "lon": -8.805,
    "timestamp": datetime.now(timezone.utc) + timedelta(seconds=30),
}

resultado_normal = evaluar_anomalia(pos_normal_1, pos_normal_2)
print("Caso normal (movimiento real de pesquero):", resultado_normal)

# Caso 2: el mismo barco "salta" a 300 km de distancia en 10 segundos
# Esto es imposible físicamente — simula un GPS falsificado
pos_salto_1 = {"lat": 42.20, "lon": -8.80, "timestamp": datetime.now(timezone.utc)}
pos_salto_2 = {
    "lat": 45.50,
    "lon": -8.80,  # ~365 km al norte
    "timestamp": datetime.now(timezone.utc) + timedelta(seconds=10),
}

resultado_anomalo = evaluar_anomalia(pos_salto_1, pos_salto_2)
print("Caso anómalo (salto GPS imposible):", resultado_anomalo)
