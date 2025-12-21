"""
Advanced Knowledge Base Manager for RAG
FAISS/ChromaDB with optimized retrievers
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

try:
    from langchain_community.document_loaders import TextLoader, PyPDFLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS, Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain.retrievers import ContextualCompressionRetriever
    from langchain.retrievers.document_compressors import LLMChainExtractor
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from ..utils.logging import setup_logger

logger = setup_logger("customer_service_24_7.rag")


class AdvancedKnowledgeBase:
    """Advanced Knowledge Base with optimized RAG"""
    
    def __init__(
        self,
        kb_path: str,
        vector_store_type: str = "faiss",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize Advanced Knowledge Base
        
        Args:
            kb_path: Path to knowledge base documents
            vector_store_type: "faiss" or "chroma"
            embedding_model: Hugging Face embedding model name
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain is required. Install with: pip install langchain langchain-community")
        
        self.kb_path = Path(kb_path)
        self.kb_path.mkdir(parents=True, exist_ok=True)
        self.vector_store_type = vector_store_type
        self.embedding_model = embedding_model
        
        # Initialize embeddings
        try:
            logger.info(f"🔄 Cargando modelo de embeddings: {embedding_model}")
            self.embeddings = HuggingFaceEmbeddings(
                model_name=embedding_model,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            logger.info("✅ Modelo de embeddings cargado")
        except Exception as e:
            logger.error(f"Error cargando embeddings: {e}")
            raise
        
        self.vector_store = None
        self.retriever = None
        self.compressed_retriever = None
        
        # Create sample KB if empty
        self._create_sample_kb()
        
        # Load and index documents
        self._load_and_index()
    
    def _create_sample_kb(self):
        """Create comprehensive sample knowledge base"""
        if list(self.kb_path.glob("*")):
            return  # KB already has files
        
        logger.info("📝 Creando base de conocimiento de ejemplo...")
        
        # Comprehensive sample documents
        sample_docs = {
            "refund_policy.txt": """POLÍTICA DE REEMBOLSOS - VERSIÓN COMPLETA

1. REEMBOLSOS DENTRO DE 30 DÍAS
   - Los clientes pueden solicitar un reembolso completo dentro de 30 días de la compra
   - El producto debe estar en su estado original, sin usar
   - Requiere comprobante de compra válido
   - Procesamiento: 5-7 días hábiles

2. REEMBOLSOS PARCIALES
   - Si el producto ha sido usado pero está defectuoso: 50-80% según estado
   - Productos con daños menores: 30-50%
   - Productos sin empaque original: máximo 70%
   - Evaluación por nuestro equipo de calidad

3. PRODUCTOS DIGITALES
   - No reembolsables después de la descarga
   - Excepción: defectos técnicos verificados
   - Reembolso completo si no se puede resolver técnicamente
   - Tiempo límite: 7 días desde compra

4. PRODUCTOS FÍSICOS ESPECIALES
   - Productos personalizados: No reembolsables
   - Productos perecederos: No reembolsables
   - Productos de higiene personal: No reembolsables si abiertos
   - Electrónicos: Requieren prueba de defecto

5. PROCESO DE REEMBOLSO
   Paso 1: Cliente contacta soporte con número de orden
   Paso 2: Verificación de elegibilidad (24 horas)
   Paso 3: Aprobación y procesamiento (5-7 días hábiles)
   Paso 4: Confirmación al método de pago original
   Paso 5: Notificación al cliente

6. MÉTODOS DE PAGO
   - Tarjeta de crédito/débito: 5-7 días hábiles
   - PayPal: 3-5 días hábiles
   - Transferencia bancaria: 7-10 días hábiles
   - Crédito de tienda: Inmediato

7. CASOS ESPECIALES
   - Pedidos duplicados: Reembolso completo inmediato
   - Productos incorrectos enviados: Reembolso + envío correcto gratuito
   - Daños en tránsito: Reembolso completo o reemplazo
   - Retrasos extremos (>14 días): Reembolso parcial opcional""",
            
            "shipping_faqs.txt": """PREGUNTAS FRECUENTES SOBRE ENVÍOS - GUÍA COMPLETA

1. TIEMPOS DE ENVÍO
   ENVÍO ESTÁNDAR:
   - Nacional: 5-7 días hábiles
   - Internacional: 10-15 días hábiles
   - Zonas remotas: +3-5 días adicionales
   
   ENVÍO EXPRESS:
   - Nacional: 2-3 días hábiles
   - Internacional: 5-7 días hábiles
   - Disponible para pedidos >$50
   
   ENVÍO SAME-DAY:
   - Solo en ciudades principales
   - Disponible para pedidos antes de 2 PM
   - Costo adicional: $15

2. RASTREO DE PEDIDOS
   - Todos los pedidos reciben número de rastreo único
   - Disponible 24 horas después de la compra
   - Actualización en tiempo real en nuestra página
   - Notificaciones por email en cada cambio de estado
   - Soporte para códigos de seguimiento de múltiples transportistas

3. PEDIDOS RETRASADOS
   POLÍTICA DE RETRASOS:
   - Retraso >2 días hábiles: Contactar soporte
   - Retraso >5 días hábiles: Reembolso parcial o envío express gratuito
   - Retraso >10 días hábiles: Reembolso completo o reemplazo
   
   CAUSAS COMUNES:
   - Condiciones climáticas extremas
   - Problemas con transportista
   - Dirección incorrecta o incompleta
   - Zonas de difícil acceso

4. CAMBIOS DE DIRECCIÓN
   - Permitido antes del envío: Gratis
   - Después del envío: $10 (si es posible)
   - No disponible si ya está en tránsito final
   - Contactar soporte con número de orden

5. PEDIDOS PERDIDOS
   PROCEDIMIENTO:
   - Esperar 5 días hábiles después de fecha estimada
   - Contactar soporte con número de orden
   - Investigación con transportista (3-5 días)
   - Resolución: Reemplazo gratuito o reembolso completo
   
   GARANTÍA:
   - Reemplazo garantizado si se confirma pérdida
   - Sin costo adicional para el cliente
   - Envío prioritario del reemplazo

6. DEVOLUCIONES DE ENVÍO
   - Cliente paga envío de devolución (excepto errores nuestros)
   - Debe usar transportista autorizado
   - Empaque original preferible
   - Procesamiento: 3-5 días después de recepción""",
            
            "order_tracking.txt": """SISTEMA DE RASTREO DE PEDIDOS - INFORMACIÓN DETALLADA

ESTADOS DEL PEDIDO:

1. PROCESANDO
   Descripción: Tu pedido está siendo preparado en nuestro almacén
   Tiempo típico: 1-2 días hábiles
   Acciones: Verificación de inventario, empaque, etiquetado
   Notificación: Email de confirmación enviado

2. ENVIADO
   Descripción: Tu pedido ha sido enviado y está en tránsito
   Tiempo típico: Inmediato después de procesamiento
   Información disponible: Número de rastreo, transportista, fecha estimada
   Acciones: Puedes rastrear en tiempo real

3. EN TRÁNSITO
   Descripción: Tu pedido está en camino a la dirección de entrega
   Tiempo típico: 3-7 días (según método de envío)
   Actualizaciones: Cada vez que cambia de ubicación
   Notificaciones: Automáticas por email

4. EN CENTRO DE DISTRIBUCIÓN
   Descripción: Tu pedido llegó al centro de distribución local
   Tiempo típico: 1 día antes de entrega
   Próximo paso: Salida para entrega
   Notificación: "Próximamente en tu área"

5. EN CAMINO PARA ENTREGA
   Descripción: Tu pedido está siendo entregado hoy
   Tiempo típico: Mismo día
   Información: Hora estimada de entrega (si disponible)
   Notificación: SMS/Email de "out for delivery"

6. ENTREGADO
   Descripción: Tu pedido ha sido entregado exitosamente
   Confirmación: Firma o foto de entrega
   Notificación: Email de confirmación
   Próximos pasos: Revisar producto, contactar si hay problemas

7. RETRASADO
   Descripción: Tu pedido está retrasado
   Causas comunes: Clima, problemas de transportista, dirección
   Acciones: Contactar soporte para opciones
   Compensación: Disponible según política

8. INTENTO DE ENTREGA FALLIDO
   Descripción: El transportista intentó entregar pero no había nadie
   Próximos pasos: Reintento automático o recoger en oficina
   Tiempo límite: 5 días hábiles
   Opciones: Reprogramar entrega o recoger en oficina

INFORMACIÓN DE RASTREO:
- Número de rastreo único por pedido
- Compatible con códigos de múltiples transportistas
- Actualización en tiempo real
- Historial completo de movimientos
- Fechas y horas precisas de cada evento""",
            
            "ticket_system.txt": """SISTEMA DE TICKETS DE SOPORTE - PROCEDIMIENTO COMPLETO

CÓMO CREAR UN TICKET:

PROCESO PASO A PASO:
1. Contacta soporte a través de:
   - Chat en línea (24/7)
   - Email: support@empresa.com
   - Teléfono: 1-800-SUPPORT
   - Formulario web

2. Proporciona información:
   - Descripción detallada del problema
   - Número de orden (si aplica)
   - Fotos o documentos relevantes
   - Tu información de contacto

3. Recibirás:
   - Número de ticket único (formato: TKT-XXXXXXXX)
   - Confirmación por email
   - Link para rastrear estado

4. Rastreo:
   - Portal web con estado en tiempo real
   - Notificaciones por email en cada actualización
   - Historial completo de interacciones

TIPOS DE TICKETS:

1. TÉCNICO
   Descripción: Problemas con productos o servicios técnicos
   Ejemplos: Producto no funciona, error en software, defectos
   Prioridad: Alta o Urgente
   Tiempo de respuesta: 2-8 horas

2. FACTURACIÓN
   Descripción: Problemas con pagos, facturas, reembolsos
   Ejemplos: Cargo incorrecto, reembolso pendiente, factura
   Prioridad: Normal o Alta
   Tiempo de respuesta: 4-24 horas

3. ENVÍO
   Descripción: Problemas con entregas y logística
   Ejemplos: Pedido retrasado, dirección incorrecta, pérdida
   Prioridad: Normal o Alta
   Tiempo de respuesta: 4-24 horas

4. GENERAL
   Descripción: Consultas generales y otras solicitudes
   Ejemplos: Preguntas sobre productos, políticas, información
   Prioridad: Baja o Normal
   Tiempo de respuesta: 24-48 horas

TIEMPOS DE RESPUESTA POR PRIORIDAD:

URGENTE:
- Tiempo: 2-4 horas
- Casos: Problemas críticos que impiden uso del producto
- Ejemplos: Servicio completamente caído, seguridad

ALTA:
- Tiempo: 4-8 horas
- Casos: Problemas que afectan funcionalidad significativa
- Ejemplos: Producto defectuoso, pago no procesado

NORMAL:
- Tiempo: 24 horas
- Casos: Problemas estándar que requieren atención
- Ejemplos: Consultas sobre productos, cambios de dirección

BAJA:
- Tiempo: 48 horas
- Casos: Consultas informativas o no críticas
- Ejemplos: Preguntas generales, solicitudes de información

ESCALACIÓN AUTOMÁTICA:
- Si no hay respuesta en tiempo límite: Escala a supervisor
- Si problema no se resuelve en 48 horas: Escala a gerente
- Si requiere expertise especializado: Escala a equipo técnico
- Cliente puede solicitar escalación manual en cualquier momento

ESTADOS DEL TICKET:
- ABIERTO: Ticket creado, esperando atención
- EN PROGRESO: Agente asignado, trabajando en solución
- PENDIENTE: Esperando información del cliente
- RESUELTO: Problema solucionado, esperando confirmación
- CERRADO: Ticket completado y confirmado por cliente
- ESCALADO: Transferido a nivel superior""",
            
            "product_info.txt": """INFORMACIÓN DE PRODUCTOS Y GARANTÍAS

GARANTÍA ESTÁNDAR:

DURACIÓN:
- Todos los productos: 1 año desde fecha de compra
- Productos premium: 2 años
- Productos electrónicos: 1 año + 90 días extendida opcional

COBERTURA:
- Defectos de fabricación: Cubierto 100%
- Fallas prematuras: Cubierto 100%
- Daños por uso normal: No cubierto
- Daños por maltrato: No cubierto
- Modificaciones no autorizadas: Anula garantía

PROCESO DE GARANTÍA:
1. Contactar soporte con número de orden
2. Descripción del problema y evidencia (fotos/video)
3. Evaluación técnica (2-3 días)
4. Aprobación y resolución:
   - Reparación gratuita
   - Reemplazo del producto
   - Reembolso completo

SOPORTE TÉCNICO:

DISPONIBILIDAD:
- Chat en línea: 24/7
- Email: support@empresa.com (respuesta en 24h)
- Teléfono: 1-800-SUPPORT (Lun-Vie 9AM-6PM)
- Base de conocimiento: Artículos y guías disponibles 24/7

SERVICIOS INCLUIDOS:
- Diagnóstico de problemas
- Guías de solución paso a paso
- Asistencia remota (cuando aplica)
- Actualizaciones de software
- Soporte de instalación

POLÍTICA DE DEVOLUCIONES:

PRODUCTOS FÍSICOS:
- Período: 30 días desde recepción
- Condición: Estado original, sin usar
- Empaque: Preferiblemente original
- Costo: Cliente paga envío de devolución (excepto errores nuestros)

PRODUCTOS DIGITALES:
- No reembolsables después de descarga
- Excepción: Defectos técnicos no resolubles
- Tiempo límite: 7 días desde compra

PRODUCTOS ESPECIALES:
- Personalizados: No reembolsables
- Perecederos: No reembolsables
- Higiene personal: No reembolsables si abiertos
- Software con licencia activada: No reembolsable

INFORMACIÓN DE PRODUCTOS:

ESPECIFICACIONES:
- Disponibles en página de producto
- Hojas técnicas descargables
- Comparativas con productos similares
- Guías de compatibilidad

VIDEOS Y RECURSOS:
- Videos tutoriales de instalación
- Guías de uso paso a paso
- FAQs específicas por producto
- Comunidad de usuarios

ACTUALIZACIONES:
- Notificaciones de nuevas versiones
- Parches de seguridad automáticos
- Mejoras de funcionalidad
- Recordatorios de mantenimiento""",
            
            "payment_processing.txt": """PROCESAMIENTO DE PAGOS Y FACTURACIÓN

MÉTODOS DE PAGO ACEPTADOS:

1. TARJETAS DE CRÉDITO/DÉBITO
   - Visa, Mastercard, American Express
   - Procesamiento: Inmediato
   - Verificación: 3D Secure cuando aplica
   - Seguridad: Encriptación SSL/TLS

2. PAYPAL
   - Procesamiento: Inmediato
   - Requiere cuenta PayPal verificada
   - Opción de pagar en cuotas (si disponible)

3. TRANSFERENCIA BANCARIA
   - Procesamiento: 1-3 días hábiles
   - Requiere confirmación manual
   - Instrucciones enviadas por email

4. CRÉDITO DE TIENDA
   - Disponible para clientes frecuentes
   - Aprobación instantánea
   - Límites según historial

PROCESAMIENTO DE PAGOS:

TIEMPOS:
- Tarjetas: Inmediato (1-2 segundos)
- PayPal: Inmediato
- Transferencia: 1-3 días hábiles
- Crédito tienda: Inmediato

VERIFICACIÓN:
- Validación de tarjeta en tiempo real
- Verificación de fondos
- Chequeo de fraude automático
- Confirmación por email

PROBLEMAS COMUNES:

PAGO RECHAZADO:
- Causas: Fondos insuficientes, tarjeta expirada, límite excedido
- Solución: Verificar con banco, intentar otro método
- Tiempo de resolución: Inmediato

CARGO DUPLICADO:
- Contactar soporte inmediatamente
- Procesamiento de reembolso: 24-48 horas
- Confirmación: Email con detalles

FACTURACIÓN INCORRECTA:
- Revisar detalles en cuenta
- Contactar soporte con número de orden
- Corrección: 1-2 días hábiles
- Nueva factura emitida

REEMBOLSOS:

PROCESAMIENTO:
- Tiempo: 5-7 días hábiles
- Método: Al método de pago original
- Confirmación: Email cuando se procesa

EXCEPCIONES:
- Transferencias bancarias: 7-10 días
- Cheques: 10-14 días
- Crédito de tienda: Inmediato

SEGURIDAD:

PROTECCIÓN:
- Encriptación de extremo a extremo
- Cumplimiento PCI DSS
- No almacenamos números de tarjeta completos
- Monitoreo de fraude 24/7

PRIVACIDAD:
- Datos de pago encriptados
- No compartimos información con terceros
- Cumplimiento GDPR
- Política de privacidad disponible""",
            
            "account_management.txt": """GESTIÓN DE CUENTAS Y PERFILES

CREACIÓN DE CUENTA:

PROCESO:
1. Registro con email o teléfono
2. Verificación de email/teléfono
3. Configuración de perfil básico
4. Activación de cuenta

BENEFICIOS:
- Historial de pedidos
- Lista de deseos
- Direcciones guardadas
- Preferencias personalizadas
- Ofertas exclusivas

GESTIÓN DE PERFIL:

INFORMACIÓN PERSONAL:
- Nombre, email, teléfono
- Dirección de facturación
- Direcciones de envío múltiples
- Preferencias de comunicación

CONFIGURACIÓN:
- Idioma preferido
- Moneda
- Zona horaria
- Notificaciones (email/SMS/push)

SEGURIDAD:

CONTRASEÑAS:
- Mínimo 8 caracteres
- Requiere mayúsculas, minúsculas, números
- Cambio cada 90 días recomendado
- Recuperación por email/teléfono

AUTENTICACIÓN:
- Verificación en dos pasos (opcional)
- Login desde dispositivos nuevos requiere verificación
- Historial de sesiones activas
- Cierre de sesión remoto disponible

PRIVACIDAD:

DATOS PERSONALES:
- Control total sobre información compartida
- Opción de eliminar cuenta
- Exportación de datos disponible
- Cumplimiento GDPR

PREFERENCIAS:
- Marketing: Opt-in/opt-out
- Cookies: Configuración personalizable
- Compartir datos: Control granular

HISTORIAL Y ACTIVIDAD:

PEDIDOS:
- Historial completo de compras
- Estado de pedidos actuales
- Facturas descargables
- Reordenar productos anteriores

ACTIVIDAD:
- Búsquedas recientes
- Productos vistos
- Lista de deseos
- Reseñas escritas

SOPORTE:
- Tickets de soporte
- Conversaciones de chat
- Llamadas registradas
- Documentos compartidos""",
            
            "return_exchange.txt": """POLÍTICA DE DEVOLUCIONES Y CAMBIOS

DEVOLUCIONES:

PERÍODO:
- Estándar: 30 días desde recepción
- Productos premium: 45 días
- Temporada navideña: Hasta 31 de enero

CONDICIONES:
- Producto en estado original
- Empaque original preferible
- Todos los accesorios incluidos
- Etiquetas y etiquetas de precio intactas

PROCESO:
1. Iniciar devolución en cuenta o contactar soporte
2. Recibir etiqueta de envío prepagada (si aplica)
3. Empaquetar producto de forma segura
4. Enviar usando transportista autorizado
5. Procesamiento: 3-5 días después de recepción
6. Reembolso o crédito aplicado

COSTOS:
- Devoluciones por error nuestro: Gratis
- Devoluciones por cambio de opinión: Cliente paga envío
- Productos defectuosos: Gratis
- Productos incorrectos enviados: Gratis + envío correcto

CAMBIOS:

PRODUCTOS ELEGIBLES:
- Disponibilidad de stock del nuevo producto
- Mismo precio o diferencia pagada
- Mismo tipo de producto

PROCESO:
1. Contactar soporte con solicitud de cambio
2. Verificar disponibilidad
3. Devolver producto original
4. Enviar nuevo producto
5. Procesar diferencia de precio (si aplica)

TIEMPO:
- Procesamiento: 5-7 días hábiles
- Envío nuevo producto: Según método elegido
- Total: 10-14 días hábiles típicamente

PRODUCTOS NO ELEGIBLES:

DEVOLUCIONES NO PERMITIDAS:
- Productos personalizados
- Productos perecederos
- Productos de higiene personal (si abiertos)
- Software con licencia activada
- Productos descargables usados
- Productos dañados por mal uso

CAMBIOS NO PERMITIDOS:
- Productos personalizados
- Productos en oferta final
- Productos fuera de stock
- Productos de diferentes categorías

REEMBOLSOS:

MÉTODO:
- Al método de pago original
- Tiempo: 5-7 días hábiles
- Confirmación: Email cuando se procesa

EXCEPCIONES:
- Transferencias bancarias: 7-10 días
- Cheques: 10-14 días
- Crédito de tienda: Inmediato

CRÉDITO DE TIENDA:
- Opción disponible para devoluciones
- Válido por 1 año
- Usable en cualquier compra
- No reembolsable a dinero""",
            
            "warranty_service.txt": """SERVICIO DE GARANTÍA Y REPARACIONES

GARANTÍA ESTÁNDAR:

COBERTURA:
- Defectos de fabricación: 100% cubierto
- Fallas prematuras: 100% cubierto
- Partes y mano de obra: Incluido
- Envío de reparación: Incluido (si aplica)

DURACIÓN:
- Productos estándar: 1 año
- Productos premium: 2 años
- Electrónicos: 1 año + 90 días opcional
- Accesorios: 6 meses

NO CUBIERTO:
- Daños por uso normal/desgaste
- Daños por maltrato o abuso
- Modificaciones no autorizadas
- Uso fuera de especificaciones
- Daños por desastres naturales
- Daños por negligencia

PROCESO DE GARANTÍA:

PASO 1: REPORTE
- Contactar soporte con número de orden
- Descripción detallada del problema
- Fotos o video del defecto
- Información del producto

PASO 2: EVALUACIÓN
- Revisión técnica (2-3 días)
- Determinación de elegibilidad
- Opciones de resolución presentadas

PASO 3: RESOLUCIÓN
Opciones disponibles:
- Reparación gratuita
- Reemplazo del producto
- Reembolso completo
- Crédito de tienda

REPARACIONES:

SERVICIO AUTORIZADO:
- Centros de servicio certificados
- Técnicos certificados
- Partes originales garantizadas
- Mismo estándar de calidad

TIEMPOS:
- Evaluación: 2-3 días
- Reparación: 5-10 días hábiles
- Envío: Según método elegido
- Total: 10-15 días hábiles típicamente

COSTOS:
- Bajo garantía: Gratis
- Fuera de garantía: Cotización previa
- Daños no cubiertos: Cliente paga

EXTENSIÓN DE GARANTÍA:

OPCIONES:
- Extensión 1 año: Disponible al comprar
- Extensión 2 años: Para productos premium
- Cobertura accidental: Opcional adicional
- Cobertura de robo: Opcional adicional

BENEFICIOS:
- Reparaciones sin costo
- Reemplazo prioritario
- Soporte técnico extendido
- Sin deducible

REEMPLAZOS:

CUANDO APLICA:
- Producto no reparable
- Múltiples fallas
- Defecto crítico de seguridad
- Producto discontinuado

PROCESO:
- Aprobación de reemplazo
- Selección de producto equivalente
- Envío prioritario
- Disposición del producto original""",
            
            "customer_rights.txt": """DERECHOS DEL CLIENTE Y POLÍTICAS

DERECHOS FUNDAMENTALES:

1. DERECHO A INFORMACIÓN CLARA
   - Información completa sobre productos
   - Precios transparentes sin cargos ocultos
   - Políticas claras y accesibles
   - Términos y condiciones comprensibles

2. DERECHO A PRIVACIDAD
   - Protección de datos personales
   - Control sobre información compartida
   - Cumplimiento GDPR y regulaciones
   - Transparencia en uso de datos

3. DERECHO A CALIDAD
   - Productos que cumplen descripción
   - Estándares de calidad garantizados
   - Resolución de problemas de calidad
   - Compensación por productos defectuosos

4. DERECHO A REEMBOLSO
   - Reembolso dentro de período establecido
   - Proceso claro y accesible
   - Tiempos de procesamiento razonables
   - Múltiples métodos de reembolso

5. DERECHO A SEGURIDAD
   - Transacciones seguras
   - Protección contra fraude
   - Datos de pago encriptados
   - Notificación de problemas de seguridad

POLÍTICAS DE PROTECCIÓN:

PROTECCIÓN DE COMPRA:
- Garantía de satisfacción
- Protección contra fraude
- Seguro de envío incluido
- Política de devolución clara

PROTECCIÓN DE DATOS:
- Encriptación de datos sensibles
- No venta de información personal
- Control de cookies y tracking
- Derecho al olvido (GDPR)

RESOLUCIÓN DE DISPUTAS:

PROCESO:
1. Contactar soporte directamente
2. Escalación a supervisor si necesario
3. Revisión por equipo de calidad
4. Mediación si requerido
5. Arbitraje como último recurso

TIEMPOS:
- Respuesta inicial: 24 horas
- Resolución estándar: 5-7 días
- Casos complejos: 14 días
- Escalación: Inmediata si solicitada

COMPENSACIONES:

CUANDO APLICA:
- Errores de nuestra parte
- Productos defectuosos
- Retrasos significativos
- Servicio deficiente verificado

TIPOS:
- Reembolso completo
- Reembolso parcial
- Crédito de tienda
- Descuentos futuros
- Productos de compensación

COMUNICACIÓN:

CANALES DISPONIBLES:
- Chat en línea 24/7
- Email: support@empresa.com
- Teléfono: 1-800-SUPPORT
- Portal de cuenta
- Redes sociales

RESPUESTAS:
- Chat: Inmediato
- Email: 24 horas
- Teléfono: Durante horario
- Portal: Actualización en tiempo real"""
        }
        
        # Write sample documents
        for filename, content in sample_docs.items():
            file_path = self.kb_path / filename
            file_path.write_text(content, encoding='utf-8')
        
        logger.info(f"✅ {len(sample_docs)} documentos de ejemplo creados")
    
    def _load_and_index(self):
        """Load documents and create optimized vector store"""
        logger.info("📚 Cargando y indexando documentos...")
        
        # Load documents
        documents = []
        loaders = []
        
        # Text files
        for txt_file in self.kb_path.glob("*.txt"):
            try:
                loader = TextLoader(str(txt_file), encoding='utf-8')
                loaders.append(loader)
            except Exception as e:
                logger.warning(f"Error cargando {txt_file}: {e}")
        
        # PDF files
        for pdf_file in self.kb_path.glob("*.pdf"):
            try:
                loader = PyPDFLoader(str(pdf_file))
                loaders.append(loader)
            except Exception as e:
                logger.warning(f"Error cargando {pdf_file}: {e}")
        
        # Load all documents
        for loader in loaders:
            try:
                docs = loader.load()
                documents.extend(docs)
            except Exception as e:
                logger.warning(f"Error procesando documentos: {e}")
        
        if not documents:
            logger.warning("⚠️ No se encontraron documentos para indexar")
            return
        
        logger.info(f"📄 {len(documents)} documentos cargados")
        
        # Split documents with optimal chunking
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        splits = text_splitter.split_documents(documents)
        logger.info(f"📑 {len(splits)} chunks creados")
        
        # Create vector store
        try:
            if self.vector_store_type == "faiss":
                self.vector_store = FAISS.from_documents(splits, self.embeddings)
                logger.info("✅ Vector store FAISS creado")
            elif self.vector_store_type == "chroma":
                persist_directory = str(self.kb_path / "chroma_db")
                self.vector_store = Chroma.from_documents(
                    splits,
                    self.embeddings,
                    persist_directory=persist_directory
                )
                logger.info("✅ Vector store Chroma creado")
            else:
                raise ValueError(f"Tipo de vector store no soportado: {self.vector_store_type}")
        except Exception as e:
            logger.error(f"Error creando vector store: {e}")
            raise
        
        # Create base retriever (top-k similarity)
        base_retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}  # Top 3 relevant chunks
        )
        
        # Create compressed retriever for better relevance
        # Note: Requires LLM for compression, using base retriever as fallback
        self.retriever = base_retriever
        self.compressed_retriever = None  # Will be set if LLM available
        
        logger.info("✅ Retriever configurado (top-k=3)")
    
    def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Search knowledge base with optimized retrieval
        
        Args:
            query: Search query
            k: Number of results
            
        Returns:
            List of relevant documents with metadata
        """
        if not self.retriever:
            logger.warning("Retriever no inicializado")
            return []
        
        try:
            # Use compressed retriever if available, else base retriever
            retriever_to_use = self.compressed_retriever or self.retriever
            
            docs = retriever_to_use.get_relevant_documents(query)
            
            results = []
            for doc in docs:
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": getattr(doc, 'score', None)
                })
            
            logger.info(f"🔍 Búsqueda completada: {len(results)} resultados para '{query}'")
            return results[:k]  # Ensure we return exactly k results
            
        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            return []
    
    def add_document(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Add new document to knowledge base
        
        Args:
            content: Document content
            metadata: Optional metadata
        """
        if not self.vector_store:
            logger.warning("Vector store no inicializado")
            return
        
        try:
            from langchain.schema import Document
            doc = Document(page_content=content, metadata=metadata or {})
            self.vector_store.add_documents([doc])
            logger.info("✅ Documento agregado a la base de conocimiento")
        except Exception as e:
            logger.error(f"Error agregando documento: {e}")



































