# 1. Usar una imagen base oficial de Python, versión ligera (slim)
FROM python:3.11-slim

# 2. Definir el directorio de trabajo dentro del contenedor
WORKDIR /app

# 3. Copiar solo el archivo de requerimientos primero (para aprovechar el caché de Docker)
COPY requirements.txt .

# 4. Instalar las dependencias sin guardar caché residual para ahorrar espacio
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar el resto del código (main.py) al contenedor
COPY . .

# 6. Exponer el puerto en el que correrá la API
EXPOSE 8000

# 7. Comando para arrancar el servidor web
# NOTA: Usamos 0.0.0.0 para que el contenedor exponga el puerto hacia afuera de su red aislada
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]