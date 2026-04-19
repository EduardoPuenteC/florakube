# 1. Usar la misma imagen ligera compartida
FROM python:3.11-slim

# 2. Directorio de trabajo
WORKDIR /app

# 3. Instalar requerimientos sin guardar caché
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiar el script
COPY . .

# 5. Ejecutar el script (una sola vez)
CMD ["python", "main.py"]