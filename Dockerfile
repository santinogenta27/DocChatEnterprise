FROM python:3.12-slim

WORKDIR /app

# Instalamos las dependencias del sistema – ¡AQUÍ ESTÁ LA CLAVE!
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    portaudio19-dev \   # ← ESTE ES EL QUE FALTABA
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiamos requirements.txt
COPY requirements.txt .

# Instalamos dependencias Python (ahora PyAudio podrá compilarse)
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código
COPY . .

# Creamos directorios (lo dejaste tú, lo mantenemos)
RUN mkdir -p data documents .docchat_cache .docchat_vectordb .docchat_memory .docchat_audit

EXPOSE 7860

# Ejecutamos la app (el puerto lo maneja app.py)
CMD ["python", "app.py"]
