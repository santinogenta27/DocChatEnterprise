/**
 * ChatPDF Widget - Chat Widget Embeddable
 * Este widget permite integrar ChatPDF Mode en cualquier website
 * Compatible con Content Security Policy (CSP) - No usa eval()
 */

(function() {
    'use strict';

    // Obtener configuración del script tag
    const scriptTag = document.currentScript || document.querySelector('script[src*="chatpdf-widget.js"]');
    if (!scriptTag) {
        console.error('ChatPDF Widget: No se pudo encontrar el script tag');
        return;
    }

    const config = {
        apiUrl: scriptTag.getAttribute('data-api-url') || 'http://127.0.0.1:7867',
        widgetId: scriptTag.getAttribute('data-widget-id') || 'chatpdf-widget-default',
        whatsappNumber: scriptTag.getAttribute('data-whatsapp-number') || null,
        calendlyLink: scriptTag.getAttribute('data-calendly-link') || null
    };

    // Normalizar URL de API
    config.apiUrl = config.apiUrl.replace(/\/$/, '');

    // Crear estilos del widget usando createElement para evitar problemas con CSP
    // Usar valores fijos en lugar de interpolación para máxima compatibilidad con CSP
    const styleElement = document.createElement('style');
    styleElement.id = 'chatpdf-widget-styles';
    
    const positionRight = config.position === 'bottom-right' || !config.position;
    const primaryColor = '#2563eb'; // Azul por defecto para ChatPDF
    
    // Construir estilos sin interpolación de variables en template strings
    let styles = '#chatpdf-widget-container{position:fixed;' + 
        (positionRight ? 'right:20px;' : 'left:20px;') + 
        'bottom:20px;z-index:10000;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;}' +
        '#chatpdf-widget-button{width:60px;height:60px;border-radius:50%;background:' + primaryColor + 
        ';border:none;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,0.15);display:flex;align-items:center;justify-content:center;transition:transform 0.2s ease,box-shadow 0.2s ease;color:white;font-size:24px;}' +
        '#chatpdf-widget-button:hover{transform:scale(1.1);box-shadow:0 6px 20px rgba(0,0,0,0.25);}' +
        '#chatpdf-widget-chat{position:absolute;' + (positionRight ? 'right:0;' : 'left:0;') + 
        'bottom:80px;width:380px;height:500px;background:white;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,0.2);display:none;flex-direction:column;overflow:hidden;}' +
        '#chatpdf-widget-chat.open{display:flex;}' +
        '.chatpdf-widget-header{background:' + primaryColor + 
        ';color:white;padding:20px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px;}' +
        '.chatpdf-widget-header-icons{display:flex;flex-direction:row;gap:12px;flex:1;align-items:center;flex-wrap:wrap;}' +
        '.chatpdf-widget-icon-link{display:flex;align-items:center;gap:6px;text-decoration:none;color:white;font-size:12px;font-weight:600;transition:opacity 0.2s ease;padding:6px 10px;border-radius:6px;background:rgba(255,255,255,0.1);}' +
        '.chatpdf-widget-icon-link:hover{opacity:0.9;background:rgba(255,255,255,0.2);}' +
        '.chatpdf-widget-icon-link svg{width:24px;height:24px;flex-shrink:0;}' +
        '.chatpdf-widget-header h3{margin:0;font-size:18px;font-weight:600;display:none;}' +
        '.chatpdf-widget-close{background:none;border:none;color:white;font-size:24px;cursor:pointer;padding:0;width:30px;height:30px;display:flex;align-items:center;justify-content:center;border-radius:50%;transition:background 0.2s ease;}' +
        '.chatpdf-widget-close:hover{background:rgba(255,255,255,0.2);}' +
        '.chatpdf-widget-messages{flex:1;overflow-y:auto;padding:20px;background:#f8f9fa;}' +
        '.chatpdf-widget-message{margin-bottom:16px;display:flex;flex-direction:column;}' +
        '.chatpdf-widget-message.user{align-items:flex-end;}' +
        '.chatpdf-widget-message.assistant{align-items:flex-start;}' +
        '.chatpdf-widget-message-bubble{max-width:80%;padding:12px 16px;border-radius:18px;word-wrap:break-word;}' +
        '.chatpdf-widget-message.user .chatpdf-widget-message-bubble{background:' + primaryColor + 
        ';color:white;border-bottom-right-radius:4px;}' +
        '.chatpdf-widget-message.assistant .chatpdf-widget-message-bubble{background:white;color:#333;border:1px solid #e0e0e0;border-bottom-left-radius:4px;}' +
        '.chatpdf-widget-input-container{padding:16px;background:white;border-top:1px solid #e0e0e0;display:flex;gap:8px;}' +
        '.chatpdf-widget-input{flex:1;padding:12px 16px;border:1px solid #e0e0e0;border-radius:24px;font-size:14px;outline:none;}' +
        '.chatpdf-widget-input:focus{border-color:' + primaryColor + ';}' +
        '.chatpdf-widget-send{width:40px;height:40px;border-radius:50%;background:' + primaryColor + 
        ';border:none;color:white;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:18px;transition:transform 0.2s ease;}' +
        '.chatpdf-widget-send:hover{transform:scale(1.1);}' +
        '.chatpdf-widget-send:disabled{opacity:0.5;cursor:not-allowed;}' +
        '.chatpdf-widget-typing{display:flex;gap:4px;padding:12px 16px;}' +
        '.chatpdf-widget-typing span{width:8px;height:8px;border-radius:50%;background:#999;animation:chatpdf-typing 1.4s infinite;}' +
        '.chatpdf-widget-typing span:nth-child(2){animation-delay:0.2s;}' +
        '.chatpdf-widget-typing span:nth-child(3){animation-delay:0.4s;}' +
        '@keyframes chatpdf-typing{0%,60%,100%{transform:translateY(0);opacity:0.7;}30%{transform:translateY(-10px);opacity:1;}}' +
        '@media (max-width:480px){#chatpdf-widget-chat{width:calc(100vw - 40px);height:calc(100vh - 100px);' + 
        (positionRight ? 'right:0;' : 'left:0;') + '}}';
    
    styleElement.textContent = styles;

    // Inyectar estilos
    document.head.appendChild(styleElement);

    // Crear elementos del widget usando createElement (más seguro para CSP)
    const container = document.createElement('div');
    container.id = 'chatpdf-widget-container';

    const chatWindow = document.createElement('div');
    chatWindow.id = 'chatpdf-widget-chat';

    const header = document.createElement('div');
    header.className = 'chatpdf-widget-header';
    
    // Crear contenedor para iconos
    const iconsContainer = document.createElement('div');
    iconsContainer.className = 'chatpdf-widget-header-icons';
    
    // Agregar icono de WhatsApp si está configurado
    if (config.whatsappNumber) {
        const whatsappLink = document.createElement('a');
        whatsappLink.href = 'https://wa.me/' + config.whatsappNumber.replace(/[^0-9]/g, '');
        whatsappLink.target = '_blank';
        whatsappLink.rel = 'noopener';
        whatsappLink.className = 'chatpdf-widget-icon-link';
        
        const whatsappText = document.createTextNode('Go to');
        whatsappLink.appendChild(whatsappText);
        
        // SVG de WhatsApp
        const whatsappSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        whatsappSvg.setAttribute('width', '24');
        whatsappSvg.setAttribute('height', '24');
        whatsappSvg.setAttribute('viewBox', '0 0 256 256');
        whatsappSvg.setAttribute('fill', 'none');
        const whatsappPath1 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        whatsappPath1.setAttribute('d', 'M128 24C74.98 24 32 66.98 32 120c0 21.62 6.28 41.72 17.16 58.68L24 232l55.89-24.32C90.79 214.95 109.12 120 224 120c0-53.02-42.98-96-96-96Z');
        whatsappPath1.setAttribute('fill', '#25D366');
        const whatsappPath2 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        whatsappPath2.setAttribute('d', 'M195.12 145.37c-2.67-1.34-15.77-7.8-18.21-8.68-2.44-.88-4.22-1.34-6 1.34s-6.89 8.68-8.43 10.48c-1.55 1.8-3.11 2.02-5.78.68-15.78-7.89-26-14.06-36.41-31.92-2.76-4.8 2.76-4.48 7.92-14.82.88-1.8.44-3.37-.22-4.68-.66-1.34-6-14.48-8.24-19.8-2.17-5.18-4.38-4.48-6-4.56-1.55-.08-3.38-.1-5.22-.1s-4.68.68-7.14 3.37c-2.44 2.76-9.3 9.08-9.3 22.14s9.52 25.72 10.84 27.52c1.34 1.8 18.74 28.58 45.23 40.12 6.32 2.72 11.24 4.36 15.09 5.58 6.34 2.07 12.11 1.78 16.68 1.08 5.08-.78 15.77-6.44 18-12.66 2.22-6.22 2.22-11.56 1.56-12.66-.66-1.1-2.44-1.8-5.1-3.14Z');
        whatsappPath2.setAttribute('fill', 'white');
        whatsappSvg.appendChild(whatsappPath1);
        whatsappSvg.appendChild(whatsappPath2);
        whatsappLink.appendChild(whatsappSvg);
        iconsContainer.appendChild(whatsappLink);
    }
    
    // Agregar icono de Calendly si está configurado
    if (config.calendlyLink) {
        const calendlyLink = document.createElement('a');
        calendlyLink.href = config.calendlyLink;
        calendlyLink.target = '_blank';
        calendlyLink.rel = 'noopener';
        calendlyLink.className = 'chatpdf-widget-icon-link';
        
        const calendlyText = document.createTextNode('Book a call on');
        calendlyLink.appendChild(calendlyText);
        
        // SVG de Calendly
        const calendlySvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        calendlySvg.setAttribute('width', '24');
        calendlySvg.setAttribute('height', '24');
        calendlySvg.setAttribute('viewBox', '0 0 256 256');
        calendlySvg.setAttribute('fill', 'none');
        const calendlyPath1 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        calendlyPath1.setAttribute('d', 'M128 0c70.58 0 128 57.42 128 128s-57.42 128-128 128S0 198.58 0 128 57.42 0 128 0Z');
        calendlyPath1.setAttribute('fill', '#00A2FF');
        const calendlyPath2 = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        calendlyPath2.setAttribute('d', 'M178.65 108.43a50.13 50.13 0 0 0-13.34-18.21 50.13 50.13 0 0 0-18.21-13.34c-12.68-5.16-26.02-3.45-37.42 4.56-15.24 10.92-22.5 29.76-19 48.03l.22.97.12.46c1.8 7.46 5.22 14.28 10.02 19.74 6.44 7.58 15.57 12.78 25.66 13.86l.73.08h.83c8.55 0 16.48-3.04 22.58-8.6 7.32-6.96 11.3-16.7 10.44-26.78l-.03-.23-.05-.23c-.88-7.63-4.53-14.51-10.65-19.32Z');
        calendlyPath2.setAttribute('fill', 'white');
        calendlySvg.appendChild(calendlyPath1);
        calendlySvg.appendChild(calendlyPath2);
        calendlyLink.appendChild(calendlySvg);
        iconsContainer.appendChild(calendlyLink);
    }
    
    // Si no hay iconos configurados, mostrar título por defecto
    if (!config.whatsappNumber && !config.calendlyLink) {
        const headerTitle = document.createElement('h3');
        headerTitle.textContent = 'ChatPDF';
        headerTitle.style.display = 'block';
        iconsContainer.appendChild(headerTitle);
    }
    
    header.appendChild(iconsContainer);

    const closeBtn = document.createElement('button');
    closeBtn.className = 'chatpdf-widget-close';
    closeBtn.setAttribute('aria-label', 'Cerrar chat');
    closeBtn.textContent = '×';
    header.appendChild(closeBtn);

    chatWindow.appendChild(header);

    const messagesContainer = document.createElement('div');
    messagesContainer.className = 'chatpdf-widget-messages';
    messagesContainer.id = 'chatpdf-widget-messages';
    chatWindow.appendChild(messagesContainer);

    const inputContainer = document.createElement('div');
    inputContainer.className = 'chatpdf-widget-input-container';

    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'chatpdf-widget-input';
    input.id = 'chatpdf-widget-input';
    input.setAttribute('placeholder', 'Escribe tu mensaje...');
    inputContainer.appendChild(input);

    const sendBtn = document.createElement('button');
    sendBtn.className = 'chatpdf-widget-send';
    sendBtn.id = 'chatpdf-widget-send';
    sendBtn.setAttribute('aria-label', 'Enviar');
    sendBtn.textContent = '➤';
    inputContainer.appendChild(sendBtn);

    chatWindow.appendChild(inputContainer);
    container.appendChild(chatWindow);

    const button = document.createElement('button');
    button.id = 'chatpdf-widget-button';
    button.setAttribute('aria-label', 'Abrir chat');
    button.textContent = '💬';
    container.appendChild(button);

    // Inyectar widget en el body
    document.body.appendChild(container);

    let isOpen = false;
    let conversationHistory = [];
    // Usar "gradio_user" para compartir documentos con la UI de Gradio (igual que Alien Mode)
    let sessionId = "gradio_user";

    // Función para agregar mensaje al chat
    function addMessage(text, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chatpdf-widget-message ${isUser ? 'user' : 'assistant'}`;
        
        const bubble = document.createElement('div');
        bubble.className = 'chatpdf-widget-message-bubble';
        bubble.textContent = text;
        
        messageDiv.appendChild(bubble);
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Guardar en historial en formato ChatPDF (tuplas)
        if (isUser) {
            conversationHistory.push([text, '']);
        } else {
            if (conversationHistory.length > 0) {
                conversationHistory[conversationHistory.length - 1][1] = text;
            }
        }
    }

    // Función para mostrar indicador de escritura
    function showTyping() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chatpdf-widget-typing';
        typingDiv.id = 'chatpdf-widget-typing-indicator';
        
        const span1 = document.createElement('span');
        const span2 = document.createElement('span');
        const span3 = document.createElement('span');
        typingDiv.appendChild(span1);
        typingDiv.appendChild(span2);
        typingDiv.appendChild(span3);
        
        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Función para ocultar indicador de escritura
    function hideTyping() {
        const typing = document.getElementById('chatpdf-widget-typing-indicator');
        if (typing) {
            typing.remove();
        }
    }

    // Función para enviar mensaje
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
            // Enviar a la API de ChatPDF
            const response = await fetch(`${config.apiUrl}/api/widget/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: sessionId,
                    history: conversationHistory.slice(0, -1) // Excluir el mensaje actual que aún no tiene respuesta
                })
            });

            hideTyping();

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // Agregar respuesta del asistente
            if (data.error) {
                addMessage('Error: ' + (data.text || data.error), false);
            } else if (data.text) {
                addMessage(data.text, false);
            } else if (data.response) {
                addMessage(data.response, false);
            } else {
                addMessage('Lo siento, no pude procesar tu mensaje. Por favor, intenta de nuevo.', false);
            }
        } catch (error) {
            hideTyping();
            console.error('ChatPDF Widget - Error enviando mensaje:', error);
            addMessage('Error de conexión. Por favor, verifica que el servidor esté corriendo en ' + config.apiUrl, false);
        } finally {
            sendBtn.disabled = false;
            input.focus();
        }
    }

    // Event listeners
    button.addEventListener('click', function() {
        isOpen = !isOpen;
        if (isOpen) {
            chatWindow.classList.add('open');
            input.focus();
            // Mostrar mensaje de bienvenida si es la primera vez
            if (conversationHistory.length === 0) {
                addMessage('Hello, I am Star Agent.\nI help you design systems capable of reaching $100K+/month.\nAsk me how the strategy works.', false);
            }
        } else {
            chatWindow.classList.remove('open');
        }
    });

    closeBtn.addEventListener('click', function() {
        isOpen = false;
        chatWindow.classList.remove('open');
    });

    sendBtn.addEventListener('click', sendMessage);

    input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Verificar salud del servidor al cargar
    fetch(`${config.apiUrl}/health`)
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            console.log('ChatPDF Widget: Servidor conectado correctamente', data);
        })
        .catch(function(error) {
            console.warn('ChatPDF Widget: No se pudo conectar al servidor. Asegúrate de que esté corriendo en', config.apiUrl);
        });

})();

