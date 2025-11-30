# 🚀 Guía Super Simple: Integra tu Chatbot en 5 Minutos

## 📋 Para Personas NO Técnicas

Esta guía está diseñada para que **cualquiera** pueda integrar su chatbot con DocChat Enterprise, incluso si no sabes programar.

---

## ✅ Paso 1: Instalar (1 minuto)

Abre tu terminal y escribe:

```bash
pip install requests
```

Eso es todo. Solo necesitas esto.

---

## ✅ Paso 2: Copiar el Código (2 minutos)

Copia este código en un archivo llamado `mi_chatbot.py`:

```python
import requests

# ==================== CONFIGURACIÓN ====================
CHATBOT_ID = "tu-chatbot-id-aqui"  # Cámbialo por tu ID
API_KEY = "tu-api-key-aqui"  # Cámbialo por tu API key
API_URL = "https://tu-servidor.com"  # URL de tu servidor

# ==================== FUNCIÓN PRINCIPAL ====================
def responder_cliente(pregunta):
    """
    Esta función la llamas cuando un cliente pregunta algo.
    """
    try:
        response = requests.post(
            f"{API_URL}/api/chatbot/{CHATBOT_ID}/query",
            json={
                "question": pregunta,
                "use_reranking": True,
                "max_chunks": 5
            },
            headers={"X-API-Key": API_KEY},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data["answer"]
    except Exception as e:
        return f"Error: {str(e)}"

# ==================== USO ====================
if __name__ == "__main__":
    pregunta = "¿Cuál es la política de devoluciones?"
    respuesta = responder_cliente(pregunta)
    print(f"Respuesta: {respuesta}")
```

---

## ✅ Paso 3: Cambiar 3 Cosas (1 minuto)

En el código que copiaste, cambia solo estas 3 líneas:

1. **CHATBOT_ID**: Pega el ID que obtuviste al registrar tu chatbot
2. **API_KEY**: Pega la API key que obtuviste al registrar tu chatbot
3. **API_URL**: Pega la URL de tu servidor DocChat Enterprise

---

## ✅ Paso 4: Usar en tu Chatbot (1 minuto)

Ahora, en tu chatbot, cuando un cliente pregunta algo, solo llama:

```python
respuesta = responder_cliente(pregunta_del_cliente)
# Muestra respuesta al cliente en tu app
```

---

## 🎉 ¡Listo!

Ya está. Tu chatbot ahora puede responder usando tus documentos privados.

---

## 💡 Ejemplos de Uso

### Ejemplo 1: Chatbot Simple

```python
# Cliente pregunta
pregunta = "¿Cuál es la política de devoluciones?"

# Tu chatbot consulta DocChat Enterprise
respuesta = responder_cliente(pregunta)

# Muestras la respuesta al cliente
print(respuesta)
```

### Ejemplo 2: Con Respuesta Directa Primero

```python
# Cliente pregunta
pregunta = "Hola"

# Tu chatbot tiene respuesta directa para saludos
if pregunta.lower() in ["hola", "buenos días", "buenas tardes"]:
    respuesta = "¡Hola! ¿En qué puedo ayudarte?"
else:
    # Si no es saludo, consulta DocChat Enterprise
    respuesta = responder_cliente(pregunta)

# Muestras la respuesta
print(respuesta)
```

---

## 🔧 Si Usas el SDK (Más Fácil)

Si prefieres usar el SDK (aún más fácil):

1. **Instalar SDK:**
```bash
pip install docchat-enterprise-sdk
```

2. **Código super simple:**
```python
from docchat.chatbot_sdk import DocChatClient

# Conectar
client = DocChatClient(
    chatbot_id="tu-id",
    api_key="tu-key",
    api_url="https://tu-servidor.com"
)

# Preguntar
respuesta = client.preguntar("¿Cuál es la política?")
print(respuesta)
```

**¡Solo 3 líneas de código!**

---

## ❓ Preguntas Frecuentes

**P: ¿Necesito saber programar?**  
R: No mucho. Solo necesitas copiar el código y cambiar 3 valores.

**P: ¿Funciona con cualquier chatbot?**  
R: Sí, funciona con cualquier chatbot que pueda hacer requests HTTP.

**P: ¿Es gratis?**  
R: Depende de tu plan. Consulta con tu proveedor.

**P: ¿Puedo probarlo antes?**  
R: Sí, puedes probar con el servidor de prueba.

---

## 🆘 ¿Necesitas Ayuda?

Si tienes problemas:
1. Verifica que CHATBOT_ID y API_KEY sean correctos
2. Verifica que el servidor esté corriendo
3. Revisa los logs de error

---

## 📚 Siguiente Paso

Una vez que funcione básico, puedes:
- Agregar caché para respuestas frecuentes
- Usar streaming para mostrar respuesta mientras se genera
- Decidir inteligentemente cuándo usar RAG

Pero para empezar, el código básico es suficiente.


