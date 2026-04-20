import os
import telebot
import requests
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# 1. Cargar configuración
load_dotenv()
TOKEN = os.environ.get("TELEGRAM_TOKEN")
API_URL = os.environ.get("API_INVENTARIO_URL")

if not TOKEN or not API_URL:
    raise RuntimeError("⚠️ Faltan variables en el archivo .env")

bot = telebot.TeleBot(TOKEN)
datos_temporales = {}

# ==========================================
# MENÚ PRINCIPAL
# ==========================================
def enviar_menu_principal(chat_id):
    """Genera y envía el panel de control central"""
    markup = InlineKeyboardMarkup()
    markup.row_width = 2 
    
    markup.add(
        InlineKeyboardButton("🌱 Mis Plantas", callback_data="menu_misplantas"),
        InlineKeyboardButton("📊 Estado General", callback_data="menu_estado")
    )
    markup.add(
        InlineKeyboardButton("➕ Agregar Planta", callback_data="menu_agregar"),
        InlineKeyboardButton("❓ Ayuda", callback_data="menu_ayuda")
    )
    
    bot.send_message(chat_id, "🪴 *Panel de Control FloraKube*\n¿Qué deseas hacer hoy?", reply_markup=markup, parse_mode="Markdown")


# ==========================================
# LÓGICA CENTRAL (Separada para reusar)
# ==========================================
def logica_misplantas(chat_id, telegram_id):
    bot.send_message(chat_id, "Consultando tu jardín virtual... 🔍")
    try:
        respuesta = requests.get(f"{API_URL}/plantas/{telegram_id}")
        if respuesta.status_code == 200:
            plantas = respuesta.json().get("plantas", [])
            if not plantas:
                bot.send_message(chat_id, "Aún no tienes plantas registradas. ¡Usa el botón de Agregar! 🌱")
                return
            
            texto_respuesta = "🌿 *Selecciona una planta para cuidarla:*\n\n"
            markup = InlineKeyboardMarkup()
            markup.row_width = 2
            
            for planta in plantas:
                nombre = planta['nombre']
                frecuencia = planta['frecuencia_riego']
                texto_respuesta += f"🪴 *{nombre}* (Agua cada {frecuencia} días)\n"
                
                # Botones específicos para cada planta
                markup.add(
                    InlineKeyboardButton(f"💧 Regar {nombre}", callback_data=f"regar_{nombre}"),
                    InlineKeyboardButton(f"✨ Abonar {nombre}", callback_data=f"abonar_{nombre}")
                )
                
            bot.send_message(chat_id, texto_respuesta, parse_mode="Markdown", reply_markup=markup)
        else:
            bot.send_message(chat_id, "No te encuentro en el sistema o no tienes plantas.")
    except Exception:
        bot.send_message(chat_id, "🚨 Error: La API de FloraKube está desconectada.")

def logica_estado(chat_id, telegram_id):
    bot.send_message(chat_id, "🔍 Revisando el invernadero, un momento...")
    try:
        respuesta = requests.get(f"{API_URL}/plantas/{telegram_id}")
        if respuesta.status_code == 200:
            plantas = respuesta.json().get("plantas", [])
            if not plantas:
                bot.send_message(chat_id, "No tienes plantas registradas aún.")
                return

            texto_estado = "📊 *Reporte General de tus plantas:*\n\n"
            for p in plantas:
                texto_estado += f"🌱 *{p['nombre']}*\n"
                texto_estado += f"   💧 Último riego: {p.get('ultimo_riego', 'Desconocido')}\n"
                texto_estado += f"   ✨ Último abono: {p.get('ultimo_fertilizante', 'Nunca')}\n\n"
            
            bot.send_message(chat_id, texto_estado, parse_mode="Markdown")
            enviar_menu_principal(chat_id) # Volvemos a mostrar el menú al terminar
        else:
            bot.send_message(chat_id, "No se encontraron datos.")
    except Exception:
        bot.send_message(chat_id, "❌ Error al conectar con la API.")


# ==========================================
# RUTAS DE MENSAJES DE TEXTO (Entradas)
# ==========================================
@bot.message_handler(commands=['start', 'menu'])
def bienvenida_y_registro(mensaje):
    chat_id = mensaje.chat.id
    telegram_id = mensaje.from_user.id
    nombre = mensaje.from_user.first_name

    bot.send_message(chat_id, "Conectando con la base de datos... ⏳")
    try:
        respuesta = requests.post(f"{API_URL}/usuarios", json={"telegram_id": telegram_id, "nombre_usuario": nombre})
        if respuesta.status_code == 200:
            bot.send_message(chat_id, f"¡Hola {nombre}! Te he registrado exitosamente. 🌱")
        elif respuesta.status_code == 400:
            bot.send_message(chat_id, f"¡Qué bueno verte de nuevo, {nombre}! 🌿")
    except Exception:
        pass # Ignoramos el error aquí para mostrar el menú de todos modos
    
    # Siempre mostramos el menú al final del start
    enviar_menu_principal(chat_id)


# ==========================================
# FLUJO DE AGREGAR PLANTA
# ==========================================
def preguntar_frecuencia(mensaje):
    chat_id = mensaje.chat.id
    nombre_planta = mensaje.text
    datos_temporales[chat_id] = {"nombre": nombre_planta}
    msg = bot.reply_to(mensaje, f"Perfecto, llamémosla '{nombre_planta}'.\n¿Cada cuántos días necesita que la riegues? (Escribe solo el número, ej. 3)")
    bot.register_next_step_handler(msg, guardar_planta_en_api)

def guardar_planta_en_api(mensaje):
    chat_id = mensaje.chat.id
    telegram_id = mensaje.from_user.id
    try:
        frecuencia = int(mensaje.text)
    except ValueError:
        msg = bot.reply_to(mensaje, "⚠️ Por favor, escribe solo un número entero. ¿Cada cuántos días?")
        bot.register_next_step_handler(msg, guardar_planta_en_api)
        return

    nombre_planta = datos_temporales[chat_id]["nombre"]
    bot.send_message(chat_id, "Guardando en el inventario... ⏳")

    try:
        respuesta = requests.post(f"{API_URL}/plantas", json={"telegram_id": telegram_id, "nombre": nombre_planta, "frecuencia_riego": frecuencia})
        if respuesta.status_code == 200:
            bot.send_message(chat_id, f"¡Listo! ✅ '{nombre_planta}' ha sido registrada.")
        else:
            bot.send_message(chat_id, "Hubo un error al registrarla.")
    except Exception:
        bot.send_message(chat_id, "🚨 Error: La API está desconectada.")
        
    if chat_id in datos_temporales:
        del datos_temporales[chat_id]
        
    enviar_menu_principal(chat_id) # Volvemos al menú


# ==========================================
# INTERCEPTOR DE TODOS LOS BOTONES
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def manejar_botones(call):
    chat_id = call.message.chat.id
    telegram_id = call.from_user.id
    
    # Quitamos el estado de "cargando" del botón en el celular
    bot.answer_callback_query(call.id)

    # 1. Rutas del Menú Principal
    if call.data == "menu_misplantas":
        logica_misplantas(chat_id, telegram_id)
        
    elif call.data == "menu_estado":
        logica_estado(chat_id, telegram_id)
        
    elif call.data == "menu_agregar":
        msg = bot.send_message(chat_id, "¡Vamos a registrar una nueva planta! 🌿\n¿Cómo se llama? (Ej. Helecho, Cactus)")
        bot.register_next_step_handler(msg, preguntar_frecuencia)
        
    elif call.data == "menu_ayuda":
        texto = "🌿 *Ayuda FloraKube*\nNavega usando los botones del `/menu`. Si en algún momento te pierdes, simplemente escribe `/menu` para volver a ver las opciones."
        bot.send_message(chat_id, texto, parse_mode="Markdown")
        enviar_menu_principal(chat_id)

    # 2. Rutas de Acción de Plantas (Regar/Abonar)
    else:
        partes = call.data.split('_', 1)
        if len(partes) != 2: return
        accion, nombre_planta = partes

        if accion == "regar":
            try:
                respuesta = requests.post(f"{API_URL}/plantas/{nombre_planta}/regar", json={"telegram_id": telegram_id})
                if respuesta.status_code == 200:
                    bot.send_message(chat_id, f"✅ ¡Listo! Registré que regaste el *{nombre_planta}*.", parse_mode="Markdown")
            except Exception:
                bot.send_message(chat_id, "❌ Error de conexión.")

        elif accion == "abonar":
            try:
                respuesta = requests.post(f"{API_URL}/plantas/{nombre_planta}/fertilizar", json={"telegram_id": telegram_id})
                if respuesta.status_code == 200:
                    bot.send_message(chat_id, f"✨ ¡Anotado! Registré el abono de *{nombre_planta}*.", parse_mode="Markdown")
            except Exception:
                bot.send_message(chat_id, "❌ Error de conexión.")

import signal
import sys

def handle_sigterm(signum, frame):
    print("🛑 SIGTERM recibido, cerrando bot limpiamente...")
    bot.stop_polling()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigterm)

if __name__ == '__main__':
    import time
    print("🤖 Dispatcher interactivo de Telegram iniciado...")
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"❌ Error: {e}")
            print("⏳ Esperando 35 segundos...")
            time.sleep(35)