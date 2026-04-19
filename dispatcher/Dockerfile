# 1. Imagen base ligera
FROM python:3.11-slim

# 2. Directorio de trabajo
WORKDIR /app

# 3. Aprovechar caché de Docker copiando solo requerimientos primero
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiar el código del bot
COPY . .

# 5. Comando de arranque (Nota: ¡No hay comando EXPOSE!)
CMD ["python", "main.py"]