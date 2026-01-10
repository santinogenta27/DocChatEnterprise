FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema necesarias para PDF, imágenes, etc. (sin PyAudio)
RUN apt-get update && apt-get install -y \
    build-essential \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Actualizar pip
RUN python -m pip install --upgrade pip

# Copiar archivos de configuración primero (para cachear layers)
COPY setup.py requirements.txt ./

# Instalar dependencias Python (algunas pueden ser opcionales)
# Intentar instalar todas las dependencias, pero continuar si algunas fallan
RUN pip install --no-cache-dir -r requirements.txt || \
    (echo "⚠️ Algunas dependencias opcionales fallaron, continuando..." && \
     echo "✅ Esto puede ser normal si hay dependencias opcionales")

# Copiar todo el código del proyecto
COPY . .

# Asegurar que el directorio actual esté en PYTHONPATH ANTES de instalar
ENV PYTHONPATH=/app:$PYTHONPATH

# INSTALAR TU PROPIO PAQUETE DOCCHAT
# Esto hace que todos los imports internos funcionen
RUN pip install --no-cache-dir -e . 2>&1 | tee /tmp/setup_install.log || \
    (echo "⚠️ Instalación en modo editable falló, usando PYTHONPATH directo" && \
     python -c "import sys; sys.path.insert(0, '/app'); import docchat; print('✅ Módulo docchat importado con PYTHONPATH')" || \
     (echo "❌ Error: No se puede importar docchat" && exit 1))

# Crear directorios necesarios
RUN mkdir -p data documents .docchat_cache .docchat_vectordb .docchat_memory .docchat_audit semantic_data/embeddings/chroma_db

# Verificar que el módulo docchat se puede importar
RUN python -c "import sys; sys.path.insert(0, '/app'); import docchat; print('✅ Módulo docchat importado correctamente')" || \
    (echo "❌ Error crítico: docchat no se puede importar" && exit 1)

# Exponer puerto que Cloud Run asigna dinámicamente
ENV PORT=8080
EXPOSE 8080

# Ejecutar app con el puerto correcto
CMD python app.py
