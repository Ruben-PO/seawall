"""
Widget de seguridad. Combina dos fuentes de alertas:
anomalías GPS (recibidas como mensajes) y escaneo de puertos
(detectado activamente revisando conexiones de red).
"""

from textual.reactive import reactive
from textual.widgets import Static

from modules.seguridad import DetectorEscaneo, VENTANA_SEGUNDOS

MAX_ALERTAS_VISIBLES = 6


class PanelSeguridad(Static):
    """Panel de seguridad: GPS spoofing + escaneo de puertos."""

    alertas: reactive[list] = reactive(list)

    def on_mount(self) -> None:
        self.detector_escaneo = DetectorEscaneo()
        self.set_interval(2.0, self.revisar_red)

    def revisar_red(self) -> None:
        for alerta in self.detector_escaneo.leer_conexiones_reales():
            self._agregar_alerta(nombre_origen=alerta["ip_origen"], detalles=alerta)

    def _agregar_alerta(self, nombre_origen: str, detalles: dict) -> None:
        nueva_alerta = {"nombre_origen": nombre_origen, "detalles": detalles}
        nuevas_alertas = [nueva_alerta] + list(self.alertas)
        self.alertas = nuevas_alertas[:MAX_ALERTAS_VISIBLES]

    def render(self) -> str:
        lineas = ["🛡️  [bold red]SEGURIDAD[/bold red]\n"]

        if not self.alertas:
            lineas.append("  [green]✓[/green] Sin anomalías detectadas")
            lineas.append("  [green]✓[/green] GPS nominal")
            lineas.append("  [green]✓[/green] Red nominal")
        else:
            for alerta in self.alertas:
                tipo = alerta["detalles"].get("tipo", "")

                if tipo == "SALTO_GPS":
                    lineas.append(f"  [bold red]⚠ GPS: {alerta['nombre_origen'][:16]}[/bold red]")
                    lineas.append(
                        f"    [yellow]{alerta['detalles']['velocidad_calculada']:.0f} kn implícitos[/yellow]"
                    )
                elif tipo == "ESCANEO_PUERTOS":
                    lineas.append(f"  [bold red]⚠ ESCANEO: {alerta['nombre_origen']}[/bold red]")
                    lineas.append(
                        f"    [yellow]{alerta['detalles']['puertos_distintos']} puertos en {VENTANA_SEGUNDOS}s[/yellow]"
                    )

        return "\n".join(lineas)
