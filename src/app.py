"""
SeaWall — Sistema de Vigilancia Marítima
Punto de entrada. Ensambla los tres paneles y gestiona
los atajos de teclado para simulaciones de seguridad.
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Header, Footer

sys.path.append(str(Path(__file__).parent))


load_dotenv()

from widgets.barcos import PanelBarcos, AlertaSeguridad
from widgets.hardware import PanelHardware
from widgets.seguridad import PanelSeguridad
from modules.seguridad import evaluar_anomalia


class SeaWallApp(App):
    """Aplicación principal de SeaWall."""

    TITLE = "SeaWall — Sistema de Vigilancia Marítima"

    BINDINGS = [
        ("s", "simular_anomalia", "Simular salto GPS"),
        ("p", "simular_escaneo", "Simular escaneo puertos"),
    ]

    CSS = """
    Screen { background: $surface; }
    PanelBarcos { border: solid cyan; padding: 1 2; width: 1fr; height: 100%; }
    PanelHardware { border: solid blue; padding: 1 2; width: 1fr; height: 100%; }
    PanelSeguridad { border: solid red; padding: 1 2; width: 1fr; height: 100%; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield PanelBarcos()
            yield PanelHardware()
            yield PanelSeguridad()
        yield Footer()

    def on_alerta_seguridad(self, mensaje: AlertaSeguridad) -> None:
        panel_seguridad = self.query_one(PanelSeguridad)
        panel_seguridad._agregar_alerta(
            nombre_origen=mensaje.nombre_origen,
            detalles=mensaje.detalles,
        )

    def action_simular_anomalia(self) -> None:
        panel_barcos = self.query_one(PanelBarcos)

        mmsi_fantasma = "999999999"
        ahora = datetime.now(timezone.utc)
        posicion_1 = {"lat": 42.20, "lon": -8.80, "timestamp": ahora}
        posicion_2 = {"lat": 45.50, "lon": -8.80, "timestamp": ahora + timedelta(seconds=10)}

        panel_barcos.ultima_posicion[mmsi_fantasma] = posicion_1
        anomalia = evaluar_anomalia(posicion_1, posicion_2)
        if anomalia:
            self.post_message(AlertaSeguridad("BARCO FANTASMA (test)", anomalia))
        panel_barcos.ultima_posicion[mmsi_fantasma] = posicion_2

    def action_simular_escaneo(self) -> None:
        panel_seguridad = self.query_one(PanelSeguridad)
        ip_atacante_simulada = "203.0.113.66"
        puertos_objetivo = [21, 22, 23, 80, 443, 3306]

        for puerto in puertos_objetivo:
            alerta = panel_seguridad.detector_escaneo.registrar_conexion(
                ip_atacante_simulada, puerto
            )
            if alerta:
                panel_seguridad._agregar_alerta(
                    nombre_origen=ip_atacante_simulada,
                    detalles=alerta,
                )


if __name__ == "__main__":
    app = SeaWallApp()
    app.run()
