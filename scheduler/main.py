import os
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

# 1. Cargar credenciales
load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
token: str = os.environ.get("TELEGRAM_TOKEN")

if not url or not key or not token:
    raise RuntimeError("⚠️ Faltan variables en el archivo .env")

supabase: Client = create_client(url, key)

def enviar_alerta_telegram(chat_id: int, mensaje: str):
    """Se comunica directamente con la API de Telegram para disparar el mensaje."""
    url_telegram = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url_telegram, json={"chat_id": chat_id, "text": mensaje})

def ejecutar_evaluacion():
    print("Iniciando evaluación de inventario botánico... 🔍")

    # Obtener la fecha y hora actual en formato UTC (el mismo que usa la base de datos)
    ahora = datetime.now(timezone.utc).isoformat()

    # 2. Consultar base de datos: "Trae todas las plantas donde el proximo_riego sea MENOR O IGUAL a hoy"
    # Usamos la sintaxis relacional de Supabase para traer también el telegram_id del usuario
    respuesta = supabase.table("plantas").select("*, usuarios(telegram_id)").lte("proximo_riego", ahora).execute()

    plantas_sedientas = respuesta.data

    if not plantas_sedientas:
        print("✅ Todas las plantas están hidratadas. No hay notificaciones pendientes.")
        return

    # 3. Procesar las plantas que necesitan agua
    print(f"⚠️ Se encontraron {len(plantas_sedientas)} plantas que necesitan agua.")

    for planta in plantas_sedientas:
        planta_id = planta["id"]
        nombre = planta["nombre"]
        frecuencia = planta["frecuencia_riego"]
        telegram_id = planta["usuarios"]["telegram_id"]

        # Enviar el mensaje
        mensaje = f"💧 ¡Hola! Es hora de regar tu: *{nombre}*.\n\nHe reiniciado el contador para dentro de {frecuencia} días."
        enviar_alerta_telegram(telegram_id, mensaje)
        print(f"Notificación enviada para '{nombre}'.")

        # 4. Reprogramar el siguiente riego
        nuevo_ultimo_riego = datetime.now(timezone.utc)
        nuevo_proximo_riego = nuevo_ultimo_riego + timedelta(days=frecuencia)

        supabase.table("plantas").update({
            "ultimo_riego": nuevo_ultimo_riego.isoformat(),
            "proximo_riego": nuevo_proximo_riego.isoformat()
        }).eq("id", planta_id).execute()

    print("Evaluación terminada con éxito. 🏁")

if __name__ == "__main__":
    ejecutar_evaluacion()
