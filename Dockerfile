FROM python:3.12-slim

WORKDIR /app

# Instalamos las dependencias del sistema necesarias
# - portaudio19-dev: obligatorio para PyAudio
# - build-essential y gcc: para compilar paquetes como PyAudio
# - curl: lo dejaste tú, útil si lo necesitás
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    portaudio19-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiamos requirements.txt primero (mejor para caché de Docker)
COPY requirements.txt .

# Instalamos dependencias de Python (ahora PyAudio podrá compilarse)
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código
COPY . .

# Creamos directorios necesarios (buena práctica, lo mantenemos)
RUN mkdir -p data documents .docchat_cache .docchat_vectordb .docchat_memory .docchat_audit

# Puerto por defecto (Render lo ignora, pero Gradio usa 7860 internamente)
EXPOSE 7860

# Ejecutamos la app (el puerto lo controla el código en app.py con os.environ.get("PORT"))
CMD ["python", "app.py"]

