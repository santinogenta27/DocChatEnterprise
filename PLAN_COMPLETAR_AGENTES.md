# 📋 PLAN COMPLETO: Completar y Simplificar los 3 Agentes

## 🎯 OBJETIVO FINAL

Transformar los 3 agentes (STEM Customer Care, Customer Business Agent, Sales AI Agent) en productos **100% funcionales** que:

✅ **Reemplazan una persona** en atención al cliente/ventas  
✅ **Responden 24/7** sin cansarse  
✅ **Convierten mejor** que un humano promedio  
✅ **Se instalan rápido** (configuración en 5-15 minutos)  
✅ **Contestan WhatsApp/Web/Instagram** automáticamente  
✅ **Hacen follow-ups** automáticos inteligentes  

---

## 📊 ESTADO ACTUAL - ANÁLISIS DETALLADO

### ✅ LO QUE YA FUNCIONA (70-80%)

#### 1. **Arquitectura Base** ✅
- ✅ Sistema RAG para conocimiento de documentos
- ✅ Integración con LLMs (Groq, OpenAI)
- ✅ Memoria conversacional
- ✅ Análisis de sentimiento
- ✅ Handoff a humano cuando detecta frustración
- ✅ Personalización básica

#### 2. **Integraciones Omnicanales** ✅ (Código existe, necesita configuración)
- ✅ WhatsApp Integration (`whatsapp_integration.py`)
- ✅ Facebook Messenger (via Meta API)
- ✅ Instagram Direct Messages (via Meta API)
- ✅ Web Chat (Gradio interface)
- ⚠️ **PROBLEMA**: Requiere configuración activa de API keys

#### 3. **Funcionalidades de Ventas** ✅
- ✅ Recomendaciones de productos
- ✅ Cross-selling y up-selling
- ✅ Manejo de objeciones
- ✅ Técnicas de cierre
- ✅ Carrito y pagos (integración con Stripe/PayPal)
- ✅ Catálogo en tiempo real

#### 4. **Comportamiento Profesional** ✅
- ✅ Personalización extrema
- ✅ Comunicación natural
- ✅ Guía del journey de compra
- ✅ Proactividad inteligente

### ❌ LO QUE FALTA O NECESITA MEJORAS (20-30%)

#### 1. **Sistema de Follow-ups Automáticos** ❌ CRÍTICO
- ❌ **NO existe código para follow-ups programados**
- ❌ **NO hay sistema de recordatorios automáticos**
- ⚠️ Existe `abandoned_cart_service.py` pero necesita verificación
- ⚠️ Existen `schedule` y `celery` en requirements.txt, pero no se usan para follow-ups

**Lo que necesita:**
- Sistema de seguimiento programado (ej: "recordar en 24h si no responde")
- Follow-ups personalizados según contexto
- Integración con calendario/notificaciones
- Base de datos para almacenar tareas pendientes

#### 2. **Configuración Simplificada** ⚠️ MEDIO
- ⚠️ **Configuración actual es compleja** (múltiples archivos JSON, .env, etc.)
- ⚠️ Requiere conocimiento técnico para configurar
- ⚠️ Múltiples API keys a configurar

**Lo que necesita:**
- Wizard de configuración inicial (5 minutos)
- Configuración en un solo lugar
- Validación automática de configuraciones
- Guías paso a paso integradas

#### 3. **Activación de Integraciones Omnicanales** ⚠️ MEDIO
- ⚠️ Código existe pero NO está activado por defecto
- ⚠️ Requiere configuración manual de webhooks
- ⚠️ Falta documentación clara paso a paso

**Lo que necesita:**
- Activación más simple (UI para conectar cuentas)
- Documentación visual paso a paso
- Testing automático de conexiones

#### 4. **Testing y Validación** ⚠️ MEDIO
- ⚠️ Falta testing exhaustivo con casos reales
- ⚠️ No hay suite de tests automatizados
- ⚠️ Falta validación de calidad de respuestas

**Lo que necesita:**
- Tests automatizados para casos comunes
- Validación de calidad de respuestas
- Sistema de feedback y mejora continua

---

## 🎯 PLAN DE IMPLEMENTACIÓN - 4 FASES

### 🔴 FASE 1: CRÍTICA - Follow-ups Automáticos (Prioridad MÁXIMA)

**Objetivo:** Implementar sistema completo de follow-ups automáticos

**Tiempo estimado:** 2-3 días

#### 1.1 Diseño del Sistema de Follow-ups

**Componentes necesarios:**
1. **Follow-up Manager** (`follow_up_manager.py`)
   - Almacena tareas de follow-up pendientes
   - Programa seguimientos según reglas
   - Ejecuta follow-ups programados

2. **Follow-up Database** (SQLite o PostgreSQL)
   - Tabla: `follow_ups`
   - Campos: `id`, `session_id`, `user_id`, `channel`, `scheduled_time`, `message_template`, `status`, `context`, `created_at`

3. **Follow-up Scheduler** (usar `schedule` o `celery`)
   - Tarea que corre cada X minutos
   - Busca follow-ups pendientes
   - Ejecuta mensajes automáticos

4. **Follow-up Templates**
   - Templates personalizables por tipo de follow-up
   - Variables dinámicas (nombre, producto, etc.)

5. **Integración con Agentes**
   - Los agentes crean follow-ups automáticamente
   - Según contexto (carrito abandonado, consulta sin respuesta, etc.)

#### 1.2 Tipos de Follow-ups a Implementar

1. **Carrito Abandonado**
   - Trigger: Usuario agrega productos al carrito pero no completa compra
   - Timing: 1 hora, 24 horas, 72 horas
   - Mensaje: Recordatorio + descuento opcional

2. **Consulta sin Respuesta**
   - Trigger: Cliente hace pregunta pero no responde en X tiempo
   - Timing: 2 horas, 24 horas
   - Mensaje: "¿Todavía necesitas ayuda con...?"

3. **Post-Compra**
   - Trigger: Después de completar compra
   - Timing: 1 día, 7 días, 30 días
   - Mensaje: "¿Cómo va tu experiencia con...?"

4. **Seguimiento de Lead**
   - Trigger: Lead calificado pero no convierte
   - Timing: 3 días, 7 días, 14 días
   - Mensaje: Ofertas personalizadas

5. **Reactivación**
   - Trigger: Cliente inactivo por X días
   - Timing: 30 días, 60 días, 90 días
   - Mensaje: "Te extrañamos, tenemos novedades..."

#### 1.3 Archivos a Crear/Modificar

**NUEVOS:**
- `docchat/common/follow_up_manager.py` (compartido por los 3 agentes)
- `docchat/common/follow_up_database.py`
- `docchat/common/follow_up_scheduler.py`
- `docchat/common/follow_up_templates.py`

**MODIFICAR:**
- `docchat/sales_ai_agent/agents/sales_ai_agent.py` (agregar creación de follow-ups)
- `docchat/customer_business_agent/agents/customer_business_agent.py` (agregar creación de follow-ups)
- `docchat/stem_customer_care/agents/stem_customer_care_agent.py` (agregar creación de follow-ups)
- `docchat/sales_ai_agent/state/customer_session.py` (agregar tracking de eventos para follow-ups)
- `app.py` (inicializar scheduler de follow-ups al inicio)

#### 1.4 Integración con Canales

- WhatsApp: Enviar follow-up via `whatsapp_integration.py`
- Web: Guardar en notificaciones o email
- Instagram/Facebook: Enviar via Meta API

---

### 🟡 FASE 2: Simplificación de Configuración (Prioridad ALTA)

**Objetivo:** Hacer que la configuración inicial sea extremadamente simple (5-15 minutos)

**Tiempo estimado:** 2-3 días

#### 2.1 Wizard de Configuración Inicial

**Componentes:**

1. **Setup Wizard UI** (en Gradio)
   - Paso 1: Información básica del negocio
     - Nombre del negocio
     - Tipo de negocio
     - Descripción
   - Paso 2: API Keys
     - Groq API Key (requerido)
     - OpenAI API Key (opcional)
     - WhatsApp credentials (opcional)
   - Paso 3: Canales a activar
     - WhatsApp: Sí/No
     - Web Chat: Sí/No
     - Instagram: Sí/No
   - Paso 4: Documentos iniciales
     - Subir documentos/catálogo
     - O conectar con Shopify/WooCommerce
   - Paso 5: Personalización básica
     - Tono de voz
     - Horarios de atención
     - Idioma

2. **Config Generator**
   - Genera `chatbot_config.json` automáticamente
   - Genera `.env` con todas las variables
   - Valida que todo esté correcto

3. **Config Validator**
   - Verifica que API keys funcionen
   - Verifica conexiones a canales
   - Muestra errores claros

#### 2.2 Archivos a Crear/Modificar

**NUEVOS:**
- `docchat/common/setup_wizard.py`
- `docchat/common/config_generator.py`
- `docchat/common/config_validator.py`
- `templates/chatbot_config_template.json`

**MODIFICAR:**
- `app.py` (agregar botón "Primera Configuración" o wizard automático si no existe config)
- Cada `*_mode.py` (simplificar inicialización con valores por defecto)

#### 2.3 Simplificación de Estructura

**Objetivo:** Reducir archivos de configuración de múltiples a uno solo

- Consolidar configuraciones en un solo `config.json` o `.env`
- Valores por defecto inteligentes
- Documentación inline en el código

---

### 🟢 FASE 3: Activación y Testing de Integraciones Omnicanales (Prioridad MEDIA-ALTA)

**Objetivo:** Asegurar que WhatsApp/Instagram/Facebook funcionen sin problemas

**Tiempo estimado:** 2 días

#### 3.1 Mejoras en Integraciones

1. **WhatsApp Integration**
   - Testing exhaustivo
   - Manejo de errores mejorado
   - Documentación paso a paso
   - UI para configurar webhook fácilmente

2. **Facebook Messenger / Instagram**
   - Similar a WhatsApp
   - Testing de ambos canales
   - Guías visuales

3. **Web Chat**
   - Widget embeddable mejorado
   - Más fácil de integrar en sitios web

#### 3.2 Testing Automatizado

- Tests unitarios para cada integración
- Tests de integración end-to-end
- Simulación de mensajes entrantes

#### 3.3 Documentación Visual

- Screenshots paso a paso
- Videos de configuración (opcional)
- Troubleshooting guide

---

### 🔵 FASE 4: Optimización y Testing Final (Prioridad MEDIA)

**Objetivo:** Asegurar calidad y rendimiento

**Tiempo estimado:** 2-3 días

#### 4.1 Testing Exhaustivo

1. **Casos de Uso Reales**
   - 20-30 conversaciones de prueba
   - Diferentes tipos de clientes
   - Diferentes escenarios (venta, objeción, error, etc.)

2. **Validación de Calidad**
   - Sistema de scoring de respuestas
   - Comparación con respuestas humanas
   - Ajustes según feedback

#### 4.2 Optimización de Performance

- Mejorar tiempos de respuesta
- Optimizar consultas RAG
- Caching inteligente

#### 4.3 Monitoreo y Logging

- Sistema de logs estructurado
- Dashboard de métricas
- Alertas automáticas

---

## 📁 ESTRUCTURA DE ARCHIVOS PROPUESTA

### Nuevos Módulos Comunes (para compartir entre los 3 agentes)

```
docchat/common/
├── __init__.py
├── follow_up_manager.py          # Gestor principal de follow-ups
├── follow_up_database.py         # Base de datos de follow-ups
├── follow_up_scheduler.py        # Scheduler de tareas
├── follow_up_templates.py        # Templates de mensajes
├── setup_wizard.py               # Wizard de configuración inicial
├── config_generator.py           # Generador de configuraciones
├── config_validator.py           # Validador de configuraciones
└── templates/
    ├── chatbot_config_template.json
    └── follow_up_templates.json
```

### Modificaciones a Módulos Existentes

```
docchat/sales_ai_agent/
├── agents/sales_ai_agent.py      # + crear follow-ups
├── state/customer_session.py     # + tracking eventos
└── services/
    └── abandoned_cart_service.py # mejorar e integrar con follow-ups

docchat/customer_business_agent/
├── agents/customer_business_agent.py  # + crear follow-ups
└── state/customer_session.py          # + tracking eventos

docchat/stem_customer_care/
├── agents/stem_customer_care_agent.py  # + crear follow-ups
└── state/customer_session.py           # + tracking eventos

app.py  # + inicializar scheduler + wizard de configuración
```

---

## 🗄️ BASE DE DATOS - Esquema Propuesto

### Tabla: follow_ups

```sql
CREATE TABLE follow_ups (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    channel VARCHAR(50) NOT NULL,  -- 'whatsapp', 'web', 'instagram', 'facebook'
    follow_up_type VARCHAR(50) NOT NULL,  -- 'abandoned_cart', 'no_response', 'post_purchase', etc.
    scheduled_time TIMESTAMP NOT NULL,
    message_template TEXT,
    context JSONB,  -- Datos adicionales (producto, carrito, etc.)
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'sent', 'cancelled', 'failed'
    attempts INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    sent_at TIMESTAMP,
    INDEX idx_scheduled_time (scheduled_time),
    INDEX idx_status (status),
    INDEX idx_session_id (session_id)
);
```

### Tabla: follow_up_history

```sql
CREATE TABLE follow_up_history (
    id SERIAL PRIMARY KEY,
    follow_up_id INT REFERENCES follow_ups(id),
    sent_at TIMESTAMP DEFAULT NOW(),
    message_sent TEXT,
    response_received BOOLEAN DEFAULT FALSE,
    response_text TEXT,
    conversion BOOLEAN DEFAULT FALSE,
    INDEX idx_follow_up_id (follow_up_id),
    INDEX idx_sent_at (sent_at)
);
```

---

## 🔄 FLUJO DE FUNCIONAMIENTO COMPLETO

### 1. Inicialización

```
Usuario ejecuta app.py
  ↓
¿Existe configuración?
  ├─ NO → Muestra Setup Wizard
  │         ↓
  │      Usuario completa wizard
  │         ↓
  │      Se genera config.json y .env
  │         ↓
  └─ SÍ → Continúa
           ↓
Inicializa agentes
           ↓
Inicializa Follow-up Scheduler (corre cada 5 minutos)
           ↓
Inicializa integraciones omnicanales (si están configuradas)
           ↓
Aplicación lista
```

### 2. Conversación Normal

```
Cliente envía mensaje (WhatsApp/Web/Instagram)
  ↓
Agente procesa mensaje
  ↓
Responde al cliente
  ↓
¿Debe crear follow-up?
  ├─ SÍ → Crea registro en tabla follow_ups
  │         (ej: carrito abandonado → follow-up en 1h, 24h, 72h)
  └─ NO → Continúa
```

### 3. Ejecución de Follow-ups

```
Scheduler (cada 5 minutos)
  ↓
Busca follow_ups con scheduled_time <= NOW() y status='pending'
  ↓
Para cada follow-up:
  ├─ Genera mensaje personalizado desde template
  ├─ Envía mensaje por canal correspondiente (WhatsApp/Web/etc.)
  ├─ Actualiza status a 'sent'
  ├─ Registra en follow_up_history
  └─ Si hay respuesta → actualiza conversación original
```

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

### Fase 1: Follow-ups (CRÍTICO)

- [ ] Crear `follow_up_manager.py`
- [ ] Crear `follow_up_database.py` con esquema SQL
- [ ] Crear `follow_up_scheduler.py` usando `schedule` o `celery`
- [ ] Crear `follow_up_templates.py` con templates predefinidos
- [ ] Modificar `sales_ai_agent.py` para crear follow-ups
- [ ] Modificar `customer_business_agent.py` para crear follow-ups
- [ ] Modificar `stem_customer_care_agent.py` para crear follow-ups
- [ ] Agregar tracking de eventos en `customer_session.py` de cada agente
- [ ] Integrar scheduler en `app.py`
- [ ] Testing: Crear follow-up → Verificar que se programa → Verificar que se envía
- [ ] Testing: Múltiples canales (WhatsApp, Web, Instagram)
- [ ] Documentación: Cómo funcionan los follow-ups

### Fase 2: Configuración Simplificada

- [ ] Crear `setup_wizard.py` con UI en Gradio
- [ ] Crear `config_generator.py`
- [ ] Crear `config_validator.py`
- [ ] Modificar `app.py` para mostrar wizard si no hay config
- [ ] Crear templates de configuración
- [ ] Testing: Wizard completo end-to-end
- [ ] Testing: Validación de API keys
- [ ] Documentación: Guía visual del wizard

### Fase 3: Integraciones Omnicanales

- [ ] Testing exhaustivo WhatsApp
- [ ] Testing exhaustivo Facebook Messenger
- [ ] Testing exhaustivo Instagram
- [ ] Mejorar manejo de errores en integraciones
- [ ] Crear UI para configurar webhooks fácilmente
- [ ] Documentación paso a paso con screenshots
- [ ] Troubleshooting guide

### Fase 4: Optimización y Testing

- [ ] Suite de tests automatizados (20-30 casos)
- [ ] Validación de calidad de respuestas
- [ ] Optimización de performance
- [ ] Sistema de logging estructurado
- [ ] Dashboard de métricas básico
- [ ] Testing final end-to-end completo

---

## ⏱️ ESTIMACIÓN DE TIEMPO TOTAL

- **Fase 1 (Follow-ups)**: 2-3 días
- **Fase 2 (Configuración)**: 2-3 días
- **Fase 3 (Integraciones)**: 2 días
- **Fase 4 (Optimización)**: 2-3 días

**TOTAL: 8-11 días de desarrollo**

---

## 🎯 RESULTADO FINAL ESPERADO

Después de completar este plan, los 3 agentes serán:

✅ **100% Funcionales** - Todo lo que prometen funciona  
✅ **Fáciles de Configurar** - 5-15 minutos de setup inicial  
✅ **Follow-ups Automáticos** - Sistema completo implementado  
✅ **Omnicanales Reales** - WhatsApp/Web/Instagram funcionando  
✅ **Listos para Vender** - Se comportan como personas reales  
✅ **Robustos** - Manejo de errores y testing completo  

---

## 📝 NOTAS IMPORTANTES

1. **Prioridad**: Seguir el orden de las fases (Fase 1 es crítica)

2. **Testing Continuo**: Probar cada componente según se implementa

3. **Documentación**: Documentar mientras se desarrolla, no después

4. **Simplicidad**: Mantener el código simple y mantenible

5. **Backwards Compatibility**: Asegurar que cambios no rompan código existente

---

## 🚀 PRÓXIMOS PASOS INMEDIATOS

1. **Revisar este plan** y confirmar que cubre todas las necesidades
2. **Empezar con Fase 1** (Follow-ups) - es lo más crítico que falta
3. **Testing incremental** - probar cada componente según se desarrolla
4. **Iterar según feedback** - ajustar según resultados de testing

