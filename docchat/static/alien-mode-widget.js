/**
 * Alien Mode Widget - Chat Widget Embeddable
 * Este widget permite integrar Alien Mode en cualquier website
 */

(function() {
    'use strict';

    // Obtener configuraciÃ³n del script tag
    const scriptTag = document.currentScript || document.querySelector('script[src*="alien-mode-widget.js"]');
    if (!scriptTag) {
        console.error('Alien Mode Widget: No se pudo encontrar el script tag');
        return;
    }

    const config = {
        apiUrl: scriptTag.getAttribute('data-api-url') || 'http://127.0.0.1:7865',
        widgetId: scriptTag.getAttribute('data-widget-id') || 'alien-widget-default',
        brandName: scriptTag.getAttribute('data-brand-name') || 'Alien Mode',
        primaryColor: scriptTag.getAttribute('data-primary-color') || '#6366f1',
        position: scriptTag.getAttribute('data-position') || 'bottom-right',
        welcomeMessage: scriptTag.getAttribute('data-welcome-message') || 'ðŸ‘‹ Â¡Hola! Soy tu asistente virtual. Â¿En quÃ© puedo ayudarte?'
    };

    // Normalizar URL de API
    config.apiUrl = config.apiUrl.replace(/\/$/, '');

    // Crear estilos del widget
    const widgetStyles = `
        <style id="alien-mode-widget-styles">
            #alien-widget-container {
                position: fixed;
                ${config.position === 'bottom-right' ? 'right: 20px;' : 'left: 20px;'}
                bottom: 20px;
                z-index: 10000;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            }

            #alien-widget-button {
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: ${config.primaryColor};
                border: none;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                display: flex;
                align-items: center;
                justify-content: center;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
                color: white;
                font-size: 24px;
            }

            #alien-widget-button:hover {
                transform: scale(1.1);
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
            }

            #alien-widget-chat {
                position: absolute;
                ${config.position === 'bottom-right' ? 'right: 0;' : 'left: 0;'}
                bottom: 80px;
                width: 380px;
                height: 500px;
                background: white;
                border-radius: 16px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                display: none;
                flex-direction: column;
                overflow: hidden;
            }

            #alien-widget-chat.open {
                display: flex;
            }

            .alien-widget-header {
                background: ${config.primaryColor};
                color: white;
                padding: 16px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .alien-widget-header h3 {
                margin: 0;
                font-size: 18px;
                font-weight: 600;
            }

            .alien-widget-close {
                background: none;
                border: none;
                color: white;
                font-size: 24px;
                cursor: pointer;
                padding: 0;
                width: 30px;
                height: 30px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: background 0.2s ease;
            }

            .alien-widget-close:hover {
                background: rgba(255, 255, 255, 0.2);
            }

            .alien-widget-messages {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                background: #f8f9fa;
            }

            .alien-widget-message {
                margin-bottom: 16px;
                display: flex;
                flex-direction: column;
            }

            .alien-widget-message.user {
                align-items: flex-end;
            }

            .alien-widget-message.assistant {
                align-items: flex-start;
            }

            .alien-widget-message-bubble {
                max-width: 80%;
                padding: 12px 16px;
                border-radius: 18px;
                word-wrap: break-word;
            }

            .alien-widget-message.user .alien-widget-message-bubble {
                background: ${config.primaryColor};
                color: white;
                border-bottom-right-radius: 4px;
            }

            .alien-widget-message.assistant .alien-widget-message-bubble {
                background: white;
                color: #333;
                border: 1px solid #e0e0e0;
                border-bottom-left-radius: 4px;
            }

            .alien-widget-input-container {
                padding: 16px;
                background: white;
                border-top: 1px solid #e0e0e0;
                display: flex;
                gap: 8px;
            }

            .alien-widget-input {
                flex: 1;
                padding: 12px 16px;
                border: 1px solid #e0e0e0;
                border-radius: 24px;
                font-size: 14px;
                outline: none;
            }

            .alien-widget-input:focus {
                border-color: ${config.primaryColor};
            }

            .alien-widget-send {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: ${config.primaryColor};
                border: none;
                color: white;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 18px;
                transition: transform 0.2s ease;
            }

            .alien-widget-send:hover {
                transform: scale(1.1);
            }

            .alien-widget-send:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }

            .alien-widget-typing {
                display: flex;
                gap: 4px;
                padding: 12px 16px;
            }

            .alien-widget-typing span {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #999;
                animation: typing 1.4s infinite;
            }

            .alien-widget-typing span:nth-child(2) {
                animation-delay: 0.2s;
            }

            .alien-widget-typing span:nth-child(3) {
                animation-delay: 0.4s;
            }

            @keyframes typing {
                0%, 60%, 100% {
                    transform: translateY(0);
                    opacity: 0.7;
                }
                30% {
                    transform: translateY(-10px);
                    opacity: 1;
                }
            }

            @media (max-width: 480px) {
                #alien-widget-chat {
                    width: calc(100vw - 40px);
                    height: calc(100vh - 100px);
                    ${config.position === 'bottom-right' ? 'right: 0;' : 'left: 0;'}
                }
            }
        </style>
    `;

    // Inyectar estilos
    document.head.insertAdjacentHTML('beforeend', widgetStyles);

    // Crear HTML del widget
    const widgetHTML = `
        <div id="alien-widget-container">
            <div id="alien-widget-chat">
                <div class="alien-widget-header">
                    <h3>${config.brandName}</h3>
                    <button class="alien-widget-close" aria-label="Cerrar chat">Ã—</button>
                </div>
                <div class="alien-widget-messages" id="alien-widget-messages"></div>
                <div class="alien-widget-input-container">
                    <input type="text" class="alien-widget-input" id="alien-widget-input" placeholder="Escribe tu mensaje..." />
                    <button class="alien-widget-send" id="alien-widget-send" aria-label="Enviar">âž¤</button>
                </div>
            </div>
            <button id="alien-widget-button" aria-label="Abrir chat">ðŸ’¬</button>
        </div>
    `;

    // Inyectar widget en el body
    document.body.insertAdjacentHTML('beforeend', widgetHTML);

    // Referencias a elementos del DOM
    const container = document.getElementById('alien-widget-container');
    const chatWindow = document.getElementById('alien-widget-chat');
    const button = document.getElementById('alien-widget-button');
    const closeBtn = document.querySelector('.alien-widget-close');
    const messagesContainer = document.getElementById('alien-widget-messages');
    const input = document.getElementById('alien-widget-input');
    const sendBtn = document.getElementById('alien-widget-send');

    let isOpen = false;
    let conversationHistory = [];

    // FunciÃ³n para agregar mensaje al chat
    function addMessage(text, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `alien-widget-message ${isUser ? 'user' : 'assistant'}`;
        
        const bubble = document.createElement('div');
        bubble.className = 'alien-widget-message-bubble';
        bubble.textContent = text;
        
        messageDiv.appendChild(bubble);
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Guardar en historial
        conversationHistory.push({
            role: isUser ? 'user' : 'assistant',
            content: text
        });
    }

    // FunciÃ³n para mostrar indicador de escritura
    function showTyping() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'alien-widget-typing';
        typingDiv.id = 'alien-widget-typing-indicator';
        typingDiv.innerHTML = '<span></span><span></span><span></span>';
        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // FunciÃ³n para ocultar indicador de escritura
    function hideTyping() {
        const typing = document.getElementById('alien-widget-typing-indicator');
        if (typing) {
            typing.remove();
        }
    }

    // FunciÃ³n para enviar mensaje
    async function sendMessage() {
        const message = input.value.trim();
        if (!message) return;

        // Agregar mensaje del usuario
        addMessage(message, true);
        input.value = '';
        sendBtn.disabled = true;

        // Mostrar indicador de escritura
        showTyping();

        try {
            // Enviar a la API
            const response = await fetch(`${config.apiUrl}/api/widget/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    widget_id: config.widgetId,
                    history: conversationHistory.slice(0, -1) // Excluir el mensaje actual
                })
            });

            hideTyping();

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // Agregar respuesta del asistente
            if (data.response) {
                addMessage(data.response, false);
            } else if (data.text) {
                addMessage(data.text, false);
            } else if (data.message) {
                addMessage(data.message, false);
            } else {
                addMessage('Lo siento, no pude procesar tu mensaje. Por favor, intenta de nuevo.', false);
            }
        } catch (error) {
            hideTyping();
            console.error('Error enviando mensaje:', error);
            addMessage('Error de conexiÃ³n. Por favor, verifica que el servidor estÃ© corriendo.', false);
        } finally {
            sendBtn.disabled = false;
            input.focus();
        }
    }

    // Event listeners
    button.addEventListener('click', () => {
        isOpen = !isOpen;
        if (isOpen) {
            chatWindow.classList.add('open');
            input.focus();
            // Mostrar mensaje de bienvenida si es la primera vez
            if (conversationHistory.length === 0) {
                addMessage(config.welcomeMessage, false);
            }
        } else {
            chatWindow.classList.remove('open');
        }
    });

    closeBtn.addEventListener('click', () => {
        isOpen = false;
        chatWindow.classList.remove('open');
    });

    sendBtn.addEventListener('click', sendMessage);

    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Verificar salud del servidor al cargar
    fetch(`${config.apiUrl}/api/widget/health`)
        .then(response => response.json())
        .then(data => {
            console.log('Alien Mode Widget: Servidor conectado correctamente', data);
        })
        .catch(error => {
            console.warn('Alien Mode Widget: No se pudo conectar al servidor. AsegÃºrate de que estÃ© corriendo en', config.apiUrl);
        });

})();
