import os
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client, Client

# 1. Cargar las variables ocultas del archivo .env
load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    raise RuntimeError("⚠️ Faltan las credenciales de Supabase en el archivo .env")

# 2. Iniciar el cliente de conexión a la base de datos
supabase: Client = create_client(url, key)

# 3. Iniciar la aplicación FastAPI
app = FastAPI(
    title="FloraKube - API de Inventario",
    description="Microservicio central para la gestión de usuarios y plantas."
)

# 4. Definir la estructura de datos que esperamos recibir (Validación)
class UsuarioNuevo(BaseModel):
    telegram_id: int
    nombre_usuario: str

class PlantaNueva(BaseModel):
    telegram_id: int
    nombre: str
    frecuencia_riego: int

class AccionPlanta(BaseModel): 
    telegram_id: int

# --- RUTAS (ENDPOINTS) ---

@app.get("/")
def estado_servidor():
    """Ruta base para comprobar que el contenedor/servidor está vivo."""
    return {"estado": "en linea", "microservicio": "api_inventario"}

@app.post("/usuarios")
def registrar_usuario(usuario: UsuarioNuevo):
    """Guarda un nuevo usuario en la base de datos de Supabase."""
    try:
        respuesta = supabase.table("usuarios").insert({
            "telegram_id": usuario.telegram_id,
            "nombre_usuario": usuario.nombre_usuario
        }).execute()
        return {"mensaje": "Usuario creado exitosamente", "datos": respuesta.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/plantas")
def registrar_planta(planta: PlantaNueva):
    """Registra una planta, asocia al usuario y calcula su próximo riego."""
    respuesta_usuario = supabase.table("usuarios").select("id").eq("telegram_id", planta.telegram_id).execute()

    if not respuesta_usuario.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado. Registrate primero.")

    usuario_uuid = respuesta_usuario.data[0]["id"]
    ahora = datetime.now(timezone.utc)
    proximo = ahora + timedelta(days=planta.frecuencia_riego)

    try:
        respuesta_planta = supabase.table("plantas").insert({
            "usuario_id": usuario_uuid,
            "nombre": planta.nombre,
            "frecuencia_riego": planta.frecuencia_riego,
            "ultimo_riego": ahora.isoformat(),
            "proximo_riego": proximo.isoformat()
        }).execute()
        return {"mensaje": "Planta agregada exitosamente", "datos": respuesta_planta.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/plantas/{telegram_id}")
def obtener_plantas(telegram_id: int):
    """Devuelve todas las plantas asociadas a un usuario específico."""
    respuesta_usuario = supabase.table("usuarios").select("id").eq("telegram_id", telegram_id).execute()
    if not respuesta_usuario.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    usuario_uuid = respuesta_usuario.data[0]["id"]
    respuesta_plantas = supabase.table("plantas").select("*").eq("usuario_id", usuario_uuid).execute()

    return {"plantas": respuesta_plantas.data}

@app.post("/plantas/{nombre_planta}/regar")
def registrar_riego(nombre_planta: str, accion: AccionPlanta):
    # 1. Buscar el usuario
    usuario = supabase.table('usuarios').select('id').eq('telegram_id', accion.telegram_id).execute()
    if not usuario.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user_id = usuario.data[0]['id']
    
    # 2. Buscar la frecuencia de la planta para poder calcular el próximo riego
    planta = supabase.table('plantas').select('frecuencia_riego').eq('nombre', nombre_planta).eq('usuario_id', user_id).execute()
    if not planta.data:
        raise HTTPException(status_code=404, detail="Planta no encontrada en tu inventario")
    frecuencia = planta.data[0]['frecuencia_riego']
    
    # 3. Calcular fechas actualizadas
    ahora = datetime.now(timezone.utc)
    nuevo_proximo_riego = ahora + timedelta(days=frecuencia)
    
    # 4. Actualizar ambos valores
    respuesta = supabase.table('plantas') \
        .update({
            "ultimo_riego": ahora.isoformat(),
            "proximo_riego": nuevo_proximo_riego.isoformat()
        }) \
        .eq('nombre', nombre_planta) \
        .eq('usuario_id', user_id) \
        .execute()
        
    return {"mensaje": "Riego registrado y cronómetro reiniciado", "fecha": ahora.isoformat()}

@app.post("/plantas/{nombre_planta}/fertilizar")
def registrar_fertilizante(nombre_planta: str, accion: AccionPlanta):
    # 1. Buscar el usuario
    usuario = supabase.table('usuarios').select('id').eq('telegram_id', accion.telegram_id).execute()
    if not usuario.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user_id = usuario.data[0]['id']
    
    # 2. Actualizar solo el fertilizante (este no requiere calcular fechas futuras)
    ahora = datetime.now(timezone.utc)
    
    respuesta = supabase.table('plantas') \
        .update({"ultimo_fertilizante": ahora.isoformat()}) \
        .eq('nombre', nombre_planta) \
        .eq('usuario_id', user_id) \
        .execute()
        
    if not respuesta.data:
        raise HTTPException(status_code=404, detail="Planta no encontrada en tu inventario")
        
    return {"mensaje": "Fertilizante registrado exitosamente", "fecha": ahora.isoformat()}

@app.delete("/plantas/{nombre_planta}")
def eliminar_planta(nombre_planta: str, telegram_id: int):
    usuario = supabase.table("usuarios").select("id").eq("telegram_id", telegram_id).execute()
    if not usuario.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user_id = usuario.data[0]["id"]

    respuesta = supabase.table("plantas").delete().eq("nombre", nombre_planta).eq("usuario_id", user_id).execute()

    if not respuesta.data:
        raise HTTPException(status_code=404, detail="Planta no encontrada")

    return {"mensaje": f"Planta '{nombre_planta}' eliminada exitosamente"}