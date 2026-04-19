import os
import telebot
import requests
from dotenv import load_dotenv

# 1. Cargar configuración
load_dotenv()
TOKEN = os.environ.get("TELEGRAM_TOKEN")
API_URL = os.environ.get("API_INVENTARIO_URL")

if not TOKEN or not API_URL:
    raise RuntimeError("⚠️ Faltan variables en el archivo .env")

# 2. Iniciar el bot
bot = telebot.TeleBot(TOKEN)

# 3. Escuchar el comando /start
@bot.message_handler(commands=['start'])
def bienvenida_y_registro(mensaje):
    telegram_id = mensaje.from_user.id
    nombre = mensaje.from_user.first_name

    bot.reply_to(mensaje, "Conectando con la base de datos de FloraKube... ⏳")

    # Intentar registrar al usuario a través de nuestro otro microservicio
    try:
        respuesta = requests.post(f"{API_URL}/usuarios", json={
            "telegram_id": telegram_id,
            "nombre_usuario": nombre
        })

        if respuesta.status_code == 200:
            bot.send_message(mensaje.chat.id, f"¡Hola {nombre}! Te he registrado exitosamente. 🌱\nPronto agregaremos el comando para registrar tus plantas.")
        elif respuesta.status_code == 400: # Si la API nos dice que ya existe
            bot.send_message(mensaje.chat.id, f"¡Qué bueno verte de nuevo, {nombre}! 🌿")
        else:
            bot.send_message(mensaje.chat.id, "Hubo un error al procesar tu registro.")

    except requests.exceptions.ConnectionError:
        # Esto pasa si olvidaste encender la API de Inventario en la otra terminal
        bot.send_message(mensaje.chat.id, "🚨 Error: El cerebro de FloraKube (API) está desconectado en este momento.")


# Diccionario temporal para guardar las respuestas mientras dura la conversación
datos_temporales = {}

@bot.message_handler(commands=['agregar'])
def iniciar_registro_planta(mensaje):
    """Paso 1: Pide el nombre de la planta"""
    msg = bot.reply_to(mensaje, "¡Vamos a registrar una nueva planta! 🌿\n¿Cómo se llama? (Ej. Helecho de la sala, Cactus)")
    bot.register_next_step_handler(msg, preguntar_frecuencia)

def preguntar_frecuencia(mensaje):
    """Paso 2: Guarda el nombre y pide la frecuencia"""
    chat_id = mensaje.chat.id
    nombre_planta = mensaje.text
    
    # Guardamos el nombre temporalmente
    datos_temporales[chat_id] = {"nombre": nombre_planta}
    
    msg = bot.reply_to(mensaje, f"Perfecto, llamémosla '{nombre_planta}'.\n¿Cada cuántos días necesita que la riegues? (Escribe solo el número, ej. 3)")
    bot.register_next_step_handler(msg, guardar_planta_en_api)

def guardar_planta_en_api(mensaje):
    """Paso 3: Envía todo a la API de Inventario"""
    chat_id = mensaje.chat.id
    telegram_id = mensaje.from_user.id
    
    try:
        frecuencia = int(mensaje.text) # Verificamos que sea un número
    except ValueError:
        msg = bot.reply_to(mensaje, "⚠️ Por favor, escribe solo un número entero. ¿Cada cuántos días?")
        bot.register_next_step_handler(msg, guardar_planta_en_api)
        return

    nombre_planta = datos_temporales[chat_id]["nombre"]
    bot.send_message(chat_id, "Guardando en el inventario... ⏳")

    # Enviamos los datos a nuestro otro microservicio (API)
    try:
        respuesta = requests.post(f"{API_URL}/plantas", json={
            "telegram_id": telegram_id,
            "nombre": nombre_planta,
            "frecuencia_riego": frecuencia
        })
        
        if respuesta.status_code == 200:
            bot.send_message(chat_id, f"¡Listo! ✅ '{nombre_planta}' ha sido registrada. Te avisaré cuando le toque agua.")
        else:
            bot.send_message(chat_id, "Hubo un error al registrarla. ¿Seguro que ya iniciaste con /start?")
            
    except requests.exceptions.ConnectionError:
        bot.send_message(chat_id, "🚨 Error: El cerebro de FloraKube (API) está desconectado.")
        
    # Limpiamos los datos temporales
    if chat_id in datos_temporales:
        del datos_temporales[chat_id]


@bot.message_handler(commands=['misplantas'])
def listar_plantas(mensaje):
    """Consulta la API y devuelve la lista de plantas del usuario"""
    chat_id = mensaje.chat.id
    telegram_id = mensaje.from_user.id
    
    bot.send_message(chat_id, "Consultando tu jardín virtual... 🔍")
    
    try:
        respuesta = requests.get(f"{API_URL}/plantas/{telegram_id}")
        
        if respuesta.status_code == 200:
            datos = respuesta.json()
            plantas = datos.get("plantas", [])
            
            if not plantas:
                bot.send_message(chat_id, "Aún no tienes plantas registradas. ¡Usa /agregar para empezar! 🌱")
                return
            
            texto_respuesta = "🌿 *Tu Inventario Botánico:*\n\n"
            for planta in plantas:
                nombre = planta['nombre']
                frecuencia = planta['frecuencia_riego']
                texto_respuesta += f"🪴 *{nombre}* (Agua cada {frecuencia} días)\n"
                
            bot.send_message(chat_id, texto_respuesta, parse_mode="Markdown")
            
        elif respuesta.status_code == 404:
            bot.send_message(chat_id, "No te encuentro en el sistema. Asegúrate de haber usado /start primero.")
        else:
            bot.send_message(chat_id, "Hubo un error misterioso al leer tu inventario. 🤔")
            
    except requests.exceptions.ConnectionError:
        bot.send_message(chat_id, "🚨 Error: La API de FloraKube está desconectada.")

@bot.message_handler(commands=['ayuda'])
def comando_ayuda(message):
    texto = (
        "🌿 *Bienvenido a tu Inventario FloraKube* 🌿\n\n"
        "Aquí tienes lo que puedo hacer por ti:\n"
        "💧 `/estado` - Muestra cómo están todas tus plantas\n"
        "🚿 `/regar [nombre]` - Registra que regaste una planta\n"
        "✨ `/fertilizante [nombre]` - Registra el último día de abono\n"
        "❓ `/ayuda` - Muestra este menú"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=['estado'])
def comando_estado(message):
    telegram_id = message.from_user.id # Agregado para buscar solo tus plantas
    bot.reply_to(message, "🔍 Revisando el invernadero, un momento...")
    try:
        # Se solicita específicamente a la API las plantas de este telegram_id
        respuesta = requests.get(f"{API_URL}/plantas/{telegram_id}")
        
        if respuesta.status_code == 200:
            datos = respuesta.json()
            plantas = datos.get("plantas", [])
            
            if not plantas:
                bot.send_message(message.chat.id, "No tienes plantas registradas aún.")
                return

            texto_estado = "🪴 *Estado de tus plantas:*\n\n"
            for p in plantas:
                texto_estado += f"🌱 *{p['nombre']}*\n"
                texto_estado += f"   💧 Último riego: {p.get('ultimo_riego', 'Desconocido')}\n"
                texto_estado += f"   ✨ Último abono: {p.get('ultimo_fertilizante', 'Nunca')}\n\n"
            
            bot.send_message(message.chat.id, texto_estado, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "No se encontraron datos. ¿Ya enviaste /start?")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error al conectar con la API: {e}")

@bot.message_handler(commands=['regar'])
def comando_regar(message):
    telegram_id = message.from_user.id # Extraemos tu ID
    partes = message.text.split(maxsplit=1)
    
    if len(partes) < 2:
        bot.reply_to(message, "⚠️ Olvidaste decirme qué planta regaste. Usa: `/regar [nombre]`", parse_mode="Markdown")
        return
        
    nombre_planta = partes[1]
    
    try:
        # Enviamos el telegram_id en formato JSON para que la API sepa de quién es la planta
        respuesta = requests.post(f"{API_URL}/plantas/{nombre_planta}/regar", json={"telegram_id": telegram_id})
        
        if respuesta.status_code == 200:
            bot.reply_to(message, f"✅ ¡Listo! Registré que regaste el *{nombre_planta}*.", parse_mode="Markdown")
        else:
            bot.reply_to(message, f"❌ No pude encontrar a '{nombre_planta}' en tu base de datos.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error de red: {e}")

@bot.message_handler(commands=['fertilizante'])
def comando_fertilizante(message):
    telegram_id = message.from_user.id # Extraemos tu ID
    partes = message.text.split(maxsplit=1)
    
    if len(partes) < 2:
        bot.reply_to(message, "⚠️ Olvidaste decirme a qué planta le pusiste abono. Usa: `/fertilizante [nombre]`", parse_mode="Markdown")
        return
        
    nombre_planta = partes[1]
    
    try:
        # Enviamos el telegram_id en formato JSON
        respuesta = requests.post(f"{API_URL}/plantas/{nombre_planta}/fertilizar", json={"telegram_id": telegram_id})
        
        if respuesta.status_code == 200:
            bot.reply_to(message, f"✨ ¡Anotado! Registré que le pusiste nutrientes al *{nombre_planta}*.", parse_mode="Markdown")
        else:
            bot.reply_to(message, f"❌ No pude encontrar a '{nombre_planta}' en tu base de datos.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error de red: {e}")
        
# 4. Mantener al bot escuchando indefinidamente
if __name__ == '__main__':
    print("🤖 Dispatcher de Telegram iniciado y esperando mensajes...")
    bot.infinity_polling()