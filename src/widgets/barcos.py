"""
Widget de tráfico marítimo. Se conecta a AISStream vía WebSocket
y detecta anomalías de posicionamiento GPS en tiempo real.
"""

import json
import os
from datetime import datetime, timezone

import websockets
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from modules.seguridad import evaluar_anomalia

API_KEY = os.getenv("AISSTREAM_API_KEY")
ZONA_AIS = [[41.80, -9.50], [43.85, -6.70]]  # Galicia: costa oeste + norte
MAX_BARCOS_VISIBLES = 8


class AlertaSeguridad(Message):
    """Mensaje emitido cuando se detecta una anomalía de cualquier tipo."""

    def __init__(self, nombre_origen: str, detalles: dict) -> None:
        self.nombre_origen = nombre_origen
        self.detalles = detalles
        super().__init__()


class PanelBarcos(Static):
    """Panel de tráfico marítimo con datos AIS reales."""

    barcos: reactive[dict] = reactive(dict)
    ultima_posicion: dict = {}

    def on_mount(self) -> None:
        self.run_worker(self.escuchar_ais(), exclusive=True)

    async def escuchar_ais(self) -> None:
        if not API_KEY:
            self.barcos = {"error": {"nombre": "Falta AISSTREAM_API_KEY"}}
            return

        try:
            async with websockets.connect("wss://stream.aisstream.io/v0/stream") as ws:
                mensaje_suscripcion = {
                    "APIKey": API_KEY,
                    "BoundingBoxes": [ZONA_AIS],
                    "FilterMessageTypes": ["PositionReport"],
                }
                await ws.send(json.dumps(mensaje_suscripcion))

                async for mensaje_json in ws:
                    mensaje = json.loads(mensaje_json)
                    if mensaje.get("MessageType") == "PositionReport":
                        self._procesar_posicion(mensaje)

        except Exception as error:
            self.barcos = {"error": {"nombre": f"Error: {error}"}}

    def _procesar_posicion(self, mensaje: dict) -> None:
        datos = mensaje["Message"]["PositionReport"]
        meta = mensaje["MetaData"]

        mmsi = str(datos.get("UserID"))
        nombre = meta.get("ShipName", "").strip() or f"MMSI {mmsi}"
        lat, lon = datos.get("Latitude"), datos.get("Longitude")

        posicion_nueva = {"lat": lat, "lon": lon, "timestamp": datetime.now(timezone.utc)}

        if mmsi in self.ultima_posicion:
            anomalia = evaluar_anomalia(self.ultima_posicion[mmsi], posicion_nueva)
            if anomalia:
                self.post_message(AlertaSeguridad(nombre, anomalia))

        self.ultima_posicion[mmsi] = posicion_nueva

        nuevos_barcos = dict(self.barcos)
        nuevos_barcos[mmsi] = {
            "nombre": nombre,
            "lat": lat,
            "lon": lon,
            "velocidad": datos.get("Sog", 0),
        }

        if len(nuevos_barcos) > MAX_BARCOS_VISIBLES:
            clave_mas_antigua = next(iter(nuevos_barcos))
            del nuevos_barcos[clave_mas_antigua]

        self.barcos = nuevos_barcos

    def render(self) -> str:
        if not self.barcos:
            return "🚢 [bold cyan]TRÁFICO MARÍTIMO[/bold cyan]\n\n[dim]Conectando a AISStream...[/dim]"

        lineas = ["🚢 [bold cyan]TRÁFICO MARÍTIMO[/bold cyan]\n"]
        for datos in self.barcos.values():
            if "lat" not in datos:
                lineas.append(f"[red]{datos['nombre']}[/red]")
                continue
            lineas.append(
                f"  [white]{datos['nombre'][:20]:<20}[/white] "
                f"[dim]{datos['velocidad']:.0f} kn[/dim]"
            )
        return "\n".join(lineas)
