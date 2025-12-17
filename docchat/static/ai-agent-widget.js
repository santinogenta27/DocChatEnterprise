/**
 * AI Agent Business Manager Widget
 * Widget de chat para sitios web de clientes
 * 
 * Uso:
 * <script src="http://tu-servidor.com/static/ai-agent-widget.js" data-config='{"scriptId":"abc123"}' async></script>
 */

(function() {
    'use strict';
    
    // Configuración por defecto
    const DEFAULT_CONFIG = {
        scriptId: null,
        apiUrl: window.location.origin || 'http://localhost:7860',
        position: 'bottom-right', // bottom-right, bottom-left
        primaryColor: '#007bff',
        welcomeMessage: '👋 ¡Hola! ¿En qué puedo ayudarte hoy?'
    };
    
    // Cargar configuración desde atributo data-config
    let widgetConfig = DEFAULT_CONFIG;
    const scriptTag = document.querySelector('script[src*="ai-agent-widget.js"]');
    if (scriptTag && scriptTag.getAttribute('data-config')) {
        try {
            widgetConfig = Object.assign({}, DEFAULT_CONFIG, JSON.parse(scriptTag.getAttribute('data-config')));
        } catch (e) {
            console.error('Error parsing widget config:', e);
        }
    }
    
    if (!widgetConfig.scriptId) {
        console.error('AI Agent Widget: scriptId is required');
        return;
    }
    
    // Estado del widget
    const state = {
        isOpen: false,
        conversationId: null,
        userId: generateUserId(),
        messages: [],
        isLoading: false
    };
    
    // Generar ID de usuario único
    function generateUserId() {
        let userId = localStorage.getItem('ai_agent_user_id');
        if (!userId) {
            userId = 'user_' + Math.random().toString(36).substr(2, 12);
            localStorage.setItem('ai_agent_user_id', userId);
        }
        return userId;
    }
    
    // Crear HTML del widget
    function createWidgetHTML() {
        const positionClass = widgetConfig.position === 'bottom-left' ? 'left' : 'right';
        
        const widgetHTML = `
            <div id="ai-agent-widget-container" class="ai-agent-widget-${positionClass}">
                <!-- Botón flotante -->
                <div id="ai-agent-widget-button" class="ai-agent-widget-btn" role="button" tabindex="0">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2Z" fill="currentColor"/>
                    </svg>
                    <span class="ai-agent-widget-badge" id="ai-agent-widget-badge" style="display: none;">0</span>
                </div>
                
                <!-- Ventana de chat -->
                <div id="ai-agent-widget-window" class="ai-agent-widget-window" style="display: none;">
                    <!-- Header -->
                    <div class="ai-agent-widget-header">
                        <div class="ai-agent-widget-header-content">
                            <div class="ai-agent-widget-avatar">🤖</div>
                            <div>
                                <div class="ai-agent-widget-title">Asistente Virtual</div>
                                <div class="ai-agent-widget-status">En línea</div>
                            </div>
                        </div>
                        <button id="ai-agent-widget-close" class="ai-agent-widget-close" aria-label="Cerrar chat">×</button>
                    </div>
                    
                    <!-- Mensajes -->
                    <div id="ai-agent-widget-messages" class="ai-agent-widget-messages">
                        <div class="ai-agent-widget-welcome">
                            ${widgetConfig.welcomeMessage}
                        </div>
                    </div>
                    
                    <!-- Input -->
                    <div class="ai-agent-widget-input-container">
                        <input 
                            type="text" 
                            id="ai-agent-widget-input" 
                            class="ai-agent-widget-input" 
                            placeholder="Escribe tu mensaje..."
                            autocomplete="off"
                        />
                        <button id="ai-agent-widget-send" class="ai-agent-widget-send" aria-label="Enviar">
                            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                                <path d="M18 2L9 11M18 2L12 18L9 11M18 2L2 8L9 11" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Inyectar HTML
        document.body.insertAdjacentHTML('beforeend', widgetHTML);
    }
    
    // Crear estilos CSS
    function createWidgetStyles() {
        const primaryColor = widgetConfig.primaryColor || '#007bff';
        const position = widgetConfig.position === 'bottom-left' ? 'left: 20px;' : 'right: 20px;';
        
        const styles = `
            <style id="ai-agent-widget-styles">
                .ai-agent-widget-right {
                    position: fixed;
                    bottom: 20px;
                    ${position}
                    z-index: 999999;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                }
                
                .ai-agent-widget-left {
                    position: fixed;
                    bottom: 20px;
                    left: 20px;
                    z-index: 999999;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                }
                
                .ai-agent-widget-btn {
                    width: 60px;
                    height: 60px;
                    border-radius: 50%;
                    background: ${primaryColor};
                    color: white;
                    border: none;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                    transition: transform 0.2s, box-shadow 0.2s;
                    position: relative;
                }
                
                .ai-agent-widget-btn:hover {
                    transform: scale(1.1);
                    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
                }
                
                .ai-agent-widget-badge {
                    position: absolute;
                    top: -5px;
                    right: -5px;
                    background: #ff4444;
                    color: white;
                    border-radius: 50%;
                    width: 24px;
                    height: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 12px;
                    font-weight: bold;
                }
                
                .ai-agent-widget-window {
                    position: absolute;
                    bottom: 80px;
                    ${position}
                    width: 380px;
                    height: 600px;
                    max-height: 80vh;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                }
                
                .ai-agent-widget-header {
                    background: ${primaryColor};
                    color: white;
                    padding: 16px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                
                .ai-agent-widget-header-content {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }
                
                .ai-agent-widget-avatar {
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.2);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 20px;
                }
                
                .ai-agent-widget-title {
                    font-weight: 600;
                    font-size: 16px;
                }
                
                .ai-agent-widget-status {
                    font-size: 12px;
                    opacity: 0.9;
                }
                
                .ai-agent-widget-close {
                    background: none;
                    border: none;
                    color: white;
                    font-size: 24px;
                    cursor: pointer;
                    width: 32px;
                    height: 32px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 4px;
                    transition: background 0.2s;
                }
                
                .ai-agent-widget-close:hover {
                    background: rgba(255, 255, 255, 0.2);
                }
                
                .ai-agent-widget-messages {
                    flex: 1;
                    overflow-y: auto;
                    padding: 16px;
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                    background: #f5f5f5;
                }
                
                .ai-agent-widget-welcome {
                    background: white;
                    padding: 12px 16px;
                    border-radius: 12px;
                    margin-bottom: 8px;
                    font-size: 14px;
                    line-height: 1.5;
                }
                
                .ai-agent-widget-message {
                    max-width: 80%;
                    padding: 12px 16px;
                    border-radius: 12px;
                    font-size: 14px;
                    line-height: 1.5;
                    word-wrap: break-word;
                }
                
                .ai-agent-widget-message.user {
                    background: ${primaryColor};
                    color: white;
                    align-self: flex-end;
                    border-bottom-right-radius: 4px;
                }
                
                .ai-agent-widget-message.assistant {
                    background: white;
                    color: #333;
                    align-self: flex-start;
                    border-bottom-left-radius: 4px;
                    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
                }
                
                .ai-agent-widget-message.loading {
                    background: white;
                    align-self: flex-start;
                    padding: 16px;
                }
                
                .ai-agent-widget-loading-dots {
                    display: inline-flex;
                    gap: 4px;
                }
                
                .ai-agent-widget-loading-dot {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: #ccc;
                    animation: ai-agent-widget-bounce 1.4s infinite ease-in-out both;
                }
                
                .ai-agent-widget-loading-dot:nth-child(1) { animation-delay: -0.32s; }
                .ai-agent-widget-loading-dot:nth-child(2) { animation-delay: -0.16s; }
                
                @keyframes ai-agent-widget-bounce {
                    0%, 80%, 100% { transform: scale(0); }
                    40% { transform: scale(1); }
                }
                
                .ai-agent-widget-input-container {
                    display: flex;
                    padding: 12px;
                    background: white;
                    border-top: 1px solid #e0e0e0;
                    gap: 8px;
                }
                
                .ai-agent-widget-input {
                    flex: 1;
                    border: 1px solid #e0e0e0;
                    border-radius: 20px;
                    padding: 10px 16px;
                    font-size: 14px;
                    outline: none;
                    transition: border-color 0.2s;
                }
                
                .ai-agent-widget-input:focus {
                    border-color: ${primaryColor};
                }
                
                .ai-agent-widget-send {
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    background: ${primaryColor};
                    color: white;
                    border: none;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: background 0.2s;
                }
                
                .ai-agent-widget-send:hover {
                    background: ${darkenColor(primaryColor, 10)};
                }
                
                .ai-agent-widget-send:disabled {
                    background: #ccc;
                    cursor: not-allowed;
                }
                
                @media (max-width: 480px) {
                    .ai-agent-widget-window {
                        width: calc(100vw - 40px);
                        height: calc(100vh - 100px);
                        ${position}
                        left: 20px;
                        right: 20px;
                    }
                }
            </style>
        `;
        
        document.head.insertAdjacentHTML('beforeend', styles);
    }
    
    // Helper para oscurecer color
    function darkenColor(color, percent) {
        const num = parseInt(color.replace('#', ''), 16);
        const amt = Math.round(2.55 * percent);
        const R = (num >> 16) + amt;
        const G = (num >> 8 & 0x00FF) + amt;
        const B = (num & 0x0000FF) + amt;
        return '#' + (0x1000000 + (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
            (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
            (B < 255 ? B < 1 ? 0 : B : 255)).toString(16).slice(1);
    }
    
    // Enviar mensaje al backend
    async function sendMessage(message) {
        if (!message.trim() || state.isLoading) return;
        
        state.isLoading = true;
        
        // Agregar mensaje del usuario a la UI
        addMessageToUI('user', message);
        
        // Mostrar indicador de carga
        const loadingId = addLoadingMessage();
        
        try {
            const response = await fetch(`${widgetConfig.apiUrl}/api/ai-agent-business/message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    widget_script_id: widgetConfig.scriptId,
                    message: message,
                    user_id: state.userId,
                    channel: 'web_widget'
                })
            });
            
            const data = await response.json();
            
            // Remover indicador de carga
            removeLoadingMessage(loadingId);
            
            if (data.error) {
                addMessageToUI('assistant', data.response || 'Lo siento, hubo un error. Intenta de nuevo.');
            } else {
                addMessageToUI('assistant', data.response);
                
                // Guardar conversation_id si es nueva
                if (data.conversation_id && !state.conversationId) {
                    state.conversationId = data.conversation_id;
                }
                
                // Si sugiere crear lead o escalar, podríamos mostrar un botón especial
                if (data.should_create_lead || data.should_escalate) {
                    // Opcional: agregar botón de acción
                }
            }
        } catch (error) {
            console.error('Error sending message:', error);
            removeLoadingMessage(loadingId);
            addMessageToUI('assistant', 'Lo siento, hubo un error de conexión. Intenta de nuevo.');
        } finally {
            state.isLoading = false;
        }
    }
    
    // Agregar mensaje a la UI
    function addMessageToUI(role, content) {
        const messagesContainer = document.getElementById('ai-agent-widget-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `ai-agent-widget-message ${role}`;
        messageDiv.textContent = content;
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    // Agregar indicador de carga
    function addLoadingMessage() {
        const messagesContainer = document.getElementById('ai-agent-widget-messages');
        const loadingDiv = document.createElement('div');
        const loadingId = 'loading-' + Date.now();
        loadingDiv.id = loadingId;
        loadingDiv.className = 'ai-agent-widget-message loading';
        loadingDiv.innerHTML = '<div class="ai-agent-widget-loading-dots"><div class="ai-agent-widget-loading-dot"></div><div class="ai-agent-widget-loading-dot"></div><div class="ai-agent-widget-loading-dot"></div></div>';
        messagesContainer.appendChild(loadingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        return loadingId;
    }
    
    // Remover indicador de carga
    function removeLoadingMessage(loadingId) {
        const loadingDiv = document.getElementById(loadingId);
        if (loadingDiv) {
            loadingDiv.remove();
        }
    }
    
    // Toggle widget
    function toggleWidget() {
        state.isOpen = !state.isOpen;
        const window = document.getElementById('ai-agent-widget-window');
        const button = document.getElementById('ai-agent-widget-button');
        
        if (state.isOpen) {
            window.style.display = 'flex';
            button.style.display = 'none';
            // Focus en input
            setTimeout(() => {
                document.getElementById('ai-agent-widget-input').focus();
            }, 100);
        } else {
            window.style.display = 'none';
            button.style.display = 'flex';
        }
    }
    
    // Inicializar widget
    function initWidget() {
        createWidgetStyles();
        createWidgetHTML();
        
        // Event listeners
        document.getElementById('ai-agent-widget-button').addEventListener('click', toggleWidget);
        document.getElementById('ai-agent-widget-close').addEventListener('click', toggleWidget);
        
        const input = document.getElementById('ai-agent-widget-input');
        const sendBtn = document.getElementById('ai-agent-widget-send');
        
        const handleSend = () => {
            const message = input.value.trim();
            if (message) {
                sendMessage(message);
                input.value = '';
            }
        };
        
        sendBtn.addEventListener('click', handleSend);
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
            }
        });
    }
    
    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWidget);
    } else {
        initWidget();
    }
    
})();

