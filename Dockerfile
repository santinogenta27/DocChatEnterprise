FROM python:3.12-slim

WORKDIR /app

# Instalamos las dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    portaudio19-dev \   # ← ESTE ES EL QUE RESUELVE PyAudio
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiamos requirements.txt
COPY requirements.txt .

# Instalamos dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código
COPY . .

# Creamos los directorios que necesitas
RUN mkdir -p data documents .docchat_cache .docchat_vectordb .docchat_memory .docchat_audit

EXPOSE 7860

# Ejecutamos la app
CMD ["python", "app.py"]
