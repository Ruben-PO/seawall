"""
Widget de monitoreo de hardware local.
Lee CPU, RAM y temperatura del sistema mediante psutil.
"""

import psutil
from textual.widgets import Static
from textual.reactive import reactive


class PanelHardware(Static):
    """Muestra métricas de hardware actualizadas cada segundo."""

    cpu_uso: reactive[float] = reactive(0.0)
    ram_uso: reactive[float] = reactive(0.0)
    ram_total: reactive[float] = reactive(0.0)
    temperatura: reactive[str] = reactive("N/D")

    def on_mount(self) -> None:
        self.set_interval(1.0, self.actualizar_datos)

    def actualizar_datos(self) -> None:
        self.cpu_uso = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()
        self.ram_uso = ram.percent
        self.ram_total = round(ram.total / (1024 ** 3), 1)

        try:
            temps = psutil.sensors_temperatures()
            if temps:
                primera_clave = list(temps.keys())[0]
                valor = temps[primera_clave][0].current
                self.temperatura = f"{valor:.1f}°C"
            else:
                self.temperatura = "N/D"
        except (AttributeError, NotImplementedError):
            self.temperatura = "N/D"

    def _barra(self, porcentaje: float, ancho: int = 10) -> str:
        llenos = int(porcentaje / 100 * ancho)
        return "█" * llenos + "░" * (ancho - llenos)

    def _color(self, pct: float) -> str:
        if pct < 50:
            return "green"
        elif pct < 80:
            return "yellow"
        return "red"

    def render(self) -> str:
        color_cpu = self._color(self.cpu_uso)
        color_ram = self._color(self.ram_uso)
        return (
            "💻 [bold blue]HARDWARE LOCAL[/bold blue]\n\n"
            f"  CPU:   [{color_cpu}]{self._barra(self.cpu_uso)}[/{color_cpu}]  {self.cpu_uso:.1f}%\n\n"
            f"  RAM:   [{color_ram}]{self._barra(self.ram_uso)}[/{color_ram}]  {self.ram_uso:.1f}%\n"
            f"         {self.ram_total} GB total\n\n"
            f"  TEMP:  [cyan]{self.temperatura}[/cyan]"
        )
