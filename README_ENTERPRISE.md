# 🚀 DocChat Enterprise - Sistema Multi-Agente RAG Avanzado

## Características Principales

### ✅ Funcionalidades Implementadas

1. **Upload Masivo (100+ PDFs)**
   - Soporte para arrastrar carpetas completas
   - Procesamiento paralelo de hasta 200 documentos
   - Análisis comparativo automático

2. **Agentes Autónomos Avanzados**
   - Generación automática de informes completos
   - Creación de presentaciones (PPT)
   - Generación de análisis en Excel
   - Workflows completos: "Analiza 80 PDFs y genera informe + PPT + Excel"

3. **Workspace Multi-Usuario**
   - Sistema de autenticación
   - Compartir documentos entre usuarios
   - Historial de chats persistente

4. **Integraciones Enterprise**
   - Gmail (leer y enviar emails)
   - Google Drive (acceso a documentos)
   - Slack (notificaciones y mensajes)
   - Notion (acceso y actualización de páginas)
   - Microsoft Teams (webhooks)

5. **Deployment On-Premise**
   - Docker Compose incluido
   - Configuración air-gapped
   - Volúmenes persistentes

6. **Sistema de Pricing**
   - Free: Funcionalidades básicas
   - Pro ($499/mes): Funcionalidades avanzadas
   - Team ($1,499/mes): Multi-usuario + integraciones
   - Enterprise ($4,999+/mes): On-premise + soporte dedicado

## Instalación Rápida

### Opción 1: Docker Compose (Recomendado)

```bash
# 1. Configurar variables de entorno
cp .env.example .env
# Editar .env y agregar OPENAI_API_KEY

# 2. Iniciar servicios
docker-compose up -d

# 3. Acceder a la aplicación
# http://localhost:7860
```

### Opción 2: Instalación Local

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar .env
export OPENAI_API_KEY=tu-clave

# 3. Ejecutar aplicación
python app.py
```

## Uso

### 1. Consulta RAG Estándar
- Sube documentos
- Haz preguntas
- Obtén respuestas verificadas con fuentes

### 2. Procesamiento Masivo
- Arrastra carpetas completas o selecciona múltiples archivos
- Procesa hasta 200 documentos simultáneamente
- Análisis comparativo automático

### 3. Workflow Completo (NUEVO)
- Ejemplo: "Analiza estos 80 PDFs y genera informe + PPT + Excel con los hallazgos"
- El sistema automáticamente:
  1. Procesa todos los documentos
  2. Genera insights usando RAG
  3. Crea informe en Excel
  4. Genera presentación PPT
  5. Entrega todos los archivos

### 4. Agentes Autónomos
- Ejecuta tareas completas usando herramientas
- Envía emails, genera reportes, actualiza bases de datos
- Integra con sistemas externos

## Configuración Avanzada

### Variables de Entorno

```bash
# API Keys
OPENAI_API_KEY=tu-clave

# Configuración de Agentes
DOCCHAT_ENABLE_AGENTS=true
DOCCHAT_AGENTIC_MODEL=gpt-4o

# Límites
DOCCHAT_MAX_UPLOAD_MB=2000  # 2GB
DOCCHAT_MAX_DOCS=200

# Memoria y Auditoría
DOCCHAT_ENABLE_MEMORY=true
DOCCHAT_ENABLE_AUDIT=true
```

## Arquitectura

```
docchat/
├── agents/              # Agentes especializados
│   ├── relevance_checker.py
│   ├── research_agent.py
│   └── verification_agent.py
├── auth/                # Autenticación y workspaces
│   ├── user_manager.py
│   └── workspace_manager.py
├── integrations/        # Integraciones enterprise
│   ├── gmail_integration.py
│   ├── drive_integration.py
│   ├── slack_integration.py
│   ├── notion_integration.py
│   └── teams_integration.py
├── tools/               # Herramientas para agentes
│   ├── email_tool.py
│   ├── report_tool.py
│   ├── presentation_tool.py
│   └── ...
├── advanced_agent.py    # Agente avanzado con workflows
├── mass_processor.py    # Procesamiento masivo
└── workflow.py          # Orquestación LangGraph
```

## Roadmap

- [x] Upload masivo (100+ PDFs)
- [x] Agentes autónomos con workflows completos
- [x] Workspace multi-usuario básico
- [x] Integraciones (Gmail, Drive, Slack, Notion, Teams)
- [x] Docker Compose on-premise
- [ ] SSO (Google + Microsoft)
- [ ] Dominio personalizado
- [ ] Sistema de pricing integrado
- [ ] API REST completa
- [ ] Dashboard de analytics

## Soporte

Para soporte o preguntas, contacta al equipo de desarrollo.

## Licencia

Proprietary - Todos los derechos reservados.



