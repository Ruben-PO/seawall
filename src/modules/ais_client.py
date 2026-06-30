"""
SeaWall — Misión 3: Cliente de AISStream
Conexión WebSocket a datos AIS en tiempo real, zona: Ría de Vigo.
"""

import asyncio
import json
import os
import websockets
from dotenv import load_dotenv

# Carga las variables del archivo .env al entorno del programa
load_dotenv()

API_KEY = os.getenv("AISSTREAM_API_KEY")

# Bounding box: [[lat_suroeste, lon_suroeste], [lat_noreste, lon_noreste]]
ZONA_VIGO = [[36.0, -10.5], [44.0, -7.0]]


async def conectar_aisstream():
    if not API_KEY:
        print("❌ ERROR: No se encontró AISSTREAM_API_KEY en el archivo .env")
        return

    print("🔌 Conectando a AISStream...")

    try:
        # 'async with' abre la conexión y la cierra automáticamente al terminar
        async with websockets.connect("wss://stream.aisstream.io/v0/stream") as ws:

            # El mensaje de suscripción: le decimos a AISStream QUÉ queremos
            mensaje_suscripcion = {
                "APIKey": API_KEY,
                "BoundingBoxes": [ZONA_VIGO],
                "FilterMessageTypes": ["PositionReport"]
            }

            await ws.send(json.dumps(mensaje_suscripcion))
            print("✅ Suscripción enviada. Esperando barcos en la ría de Vigo...\n")

            # CORREGIDO: 'async for' con espacio. Escucha mensajes indefinidamente
            async for mensaje_json in ws:
                mensaje = json.loads(mensaje_json)

                datos = mensaje["Message"]["PositionReport"]
                meta = mensaje["MetaData"]

                nombre = meta.get("ShipName", "DESCONOCIDO").strip()
                mmsi = datos.get("UserID")
                lat = datos.get("Latitude")
                lon = datos.get("Longitude")
                velocidad = datos.get("Sog")

                print(
                    f"🚢 {nombre or 'Sin nombre'} | "
                    f"MMSI: {mmsi} | "
                    f"Lat: {lat:.4f}, Lon: {lon:.4f} | "
                    f"Velocidad: {velocidad} nudos"
                )

    except Exception as e:
        print(f"❌ Error en la conexión o ejecución: {e}")


if __name__ == "__main__":
    asyncio.run(conectar_aisstream())
