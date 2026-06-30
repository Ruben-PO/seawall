"""
SeaWall — Misión 4: Detección de anomalías GPS
Calcula si el movimiento entre dos posiciones de un barco es físicamente posible.
"""

import math
from collections import defaultdict
from datetime import datetime, timezone

import psutil

# Si un barco "se mueve" más rápido que esto, algo no cuadra.
# 100 nudos es generoso: hasta los barcos rápidos del mundo
# raramente superan los 50-60 nudos.
VELOCIDAD_SOSPECHOSA_NUDOS = 100.0

# Si la misma IP toca más de este número de puertos distintos
# en la ventana de tiempo, lo consideramos un escaneo
UMBRAL_PUERTOS_DISTINTOS = 5

# Ventana de tiempo en segundos durante la que "recordamos" actividad
VENTANA_SEGUNDOS = 10


def distancia_haversine_nm(lat1, lon1, lat2, lon2) -> float:
    """
    Calcula la distancia entre dos puntos GPS en millas náuticas (nm),
    la unidad estándar en navegación marítima.

    La fórmula de Haversine tiene en cuenta la curvatura de la Tierra:
    una resta simple de coordenadas daría resultados incorrectos,
    sobre todo a distancias grandes.
    """
    RADIO_TIERRA_NM = 3440.065  # Radio de la Tierra en millas náuticas

    # Convertimos grados a radianes, que es lo que requieren
    # las funciones trigonométricas de Python (math.sin, math.cos)
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)

    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad

    # La fórmula en sí — no necesitas memorizarla, solo entender
    # que mide la distancia angular entre los dos puntos
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    return RADIO_TIERRA_NM * c


def evaluar_anomalia(posicion_anterior: dict, posicion_nueva: dict) -> dict | None:
    """
    Compara dos posiciones consecutivas del MISMO barco y determina
    si el "salto" entre ellas es sospechoso.

    Recibe diccionarios con: lat, lon, timestamp (datetime)
    Devuelve None si todo es normal, o un dict con detalles si hay alerta.
    """
    distancia_nm = distancia_haversine_nm(
        posicion_anterior["lat"], posicion_anterior["lon"],
        posicion_nueva["lat"], posicion_nueva["lon"],
    )

    # Calculamos cuánto tiempo pasó entre los dos mensajes, en horas
    delta_segundos = (
        posicion_nueva["timestamp"] - posicion_anterior["timestamp"]
    ).total_seconds()

    # Evitamos dividir por cero si llegan dos mensajes en el mismo instante
    if delta_segundos <= 0:
        return None

    delta_horas = delta_segundos / 3600
    velocidad_implicita = distancia_nm / delta_horas  # nudos = nm/hora

    if velocidad_implicita > VELOCIDAD_SOSPECHOSA_NUDOS:
        return {
            "tipo": "SALTO_GPS",
            "velocidad_calculada": round(velocidad_implicita, 1),
            "distancia_nm": round(distancia_nm, 1),
            "segundos_transcurridos": round(delta_segundos, 1),
        }

    return None


class DetectorEscaneo:
    """
    Mantiene un historial reciente de qué puertos ha tocado cada IP,
    y decide si el patrón parece un escaneo.

    Usamos una clase (en vez de funciones sueltas) porque este detector
    necesita "memoria" entre llamadas: recordar lo que vio hace
    unos segundos para compararlo con lo que ve ahora.
    """

    def __init__(self) -> None:
        self.historial: dict[str, list[tuple[int, datetime]]] = defaultdict(list)
        # Recuerda qué IPs ya dispararon una alerta, para no repetirla
        # mientras el mismo ataque siga activo.
        self.ips_ya_alertadas: set[str] = set()

    def registrar_conexion(self, ip_remota: str, puerto: int) -> dict | None:
        """
        Registra que 'ip_remota' tocó 'puerto' ahora mismo.
        Devuelve una alerta solo la PRIMERA vez que se cruza el umbral
        para esa IP — no en cada evento posterior mientras siga activa.
        """
        ahora = datetime.now(timezone.utc)
        self.historial[ip_remota].append((puerto, ahora))
        self.historial[ip_remota] = [
            (p, t) for (p, t) in self.historial[ip_remota]
            if (ahora - t).total_seconds() <= VENTANA_SEGUNDOS
        ]
        puertos_unicos = {p for (p, _) in self.historial[ip_remota]}

        # Si la IP ya NO tiene actividad reciente que supere el umbral,
        # la "olvidamos" — así, si vuelve a atacar más tarde, sí generará
        # una alerta nueva en vez de quedarse silenciada para siempre.
        if len(puertos_unicos) < UMBRAL_PUERTOS_DISTINTOS:
            self.ips_ya_alertadas.discard(ip_remota)
            return None

        # A partir de aquí, sabemos que SÍ supera el umbral.
        # Solo alertamos si es la primera vez que lo cruza.
        if ip_remota in self.ips_ya_alertadas:
            return None  # Ya alertamos sobre esta IP, no repetimos

        self.ips_ya_alertadas.add(ip_remota)
        return {
            "tipo": "ESCANEO_PUERTOS",
            "ip_origen": ip_remota,
            "puertos_distintos": len(puertos_unicos),
            "puertos": sorted(puertos_unicos),
        }

    def leer_conexiones_reales(self) -> list[dict]:
        """
        Consulta las conexiones de red ACTIVAS de la máquina con psutil,
        y las evalúa una por una contra registrar_conexion().

        Devuelve una lista de alertas (puede estar vacía).
        """
        alertas = []

        try:
            conexiones = psutil.net_connections(kind="inet")
        except (psutil.AccessDenied, PermissionError):
            # Esperado en muchos sistemas sin privilegios elevados.
            # No es un error fatal, simplemente no podemos ver todo.
            return []

        for conexion in conexiones:
            # raddr = "remote address" — solo nos interesan conexiones
            # que SÍ tienen una IP remota (descarta sockets en escucha local)
            if conexion.raddr:
                ip_remota = conexion.raddr.ip
                puerto = conexion.raddr.port

                alerta = self.registrar_conexion(ip_remota, puerto)
                if alerta:
                    alertas.append(alerta)

        return alertas
