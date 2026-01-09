# ==========================
# Imagen base
# ==========================
FROM python:3.12-slim

# ==========================
# Directorio de trabajo
# ==========================
WORKDIR /app

# ==========================
# Instalar dependencias del sistema
# necesarias para PyAudio y otras librerías
# ==========================
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    portaudio19-dev \
    libasound2-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ==========================
# Actualizar pip
# ==========================
RUN python -m pip install --upgrade pip

# ==========================
# Copiar y instalar dependencias Python
# ==========================
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ==========================
# Copiar todo el código
# ==========================
COPY . .

# ==========================
# Crear directorios necesarios
# ==========================
RUN mkdir -p data documents .docchat_cache .docchat_vectordb .docchat_memory .docchat_audit

# ==========================
# Exponer puerto
# ==========================
EXPOSE 7860

# ==========================
# Comando para ejecutar la app
# ==========================
CMD ["python", "app.py"]
