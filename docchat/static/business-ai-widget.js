/**
 * Business AI Omnicanal Widget
 * Widget embeddable para sitios web - Agente de ventas + soporte 24/7
 * 
 * Basado en Mix-ECom, Retail-GPT, CSALES y MegaChat papers
 * 
 * Uso:
 * <script src="https://tu-servidor.com/static/business-ai-widget.js" 
 *         data-api-url="https://tu-servidor.com" 
 *         data-widget-id="tu-widget-id" 
 *         async></script>
 */

(function() {
    'use strict';
    
    // Configuración por defecto
    const DEFAULT_CONFIG = {
        apiUrl: window.location.origin || 'http://localhost:7860',
        widgetId: null,
        position: 'bottom-right', // bottom-right, bottom-left
        primaryColor: '#007bff',
        welcomeMessage: '👋 ¡Hola! Soy tu asistente virtual. ¿En qué puedo ayudarte hoy?',
        brandName: 'Tu Marca',
        language: 'es'
    };
    
    // Cargar configuración desde atributos data-*
    let widgetConfig = { ...DEFAULT_CONFIG };
    const scriptTag = document.querySelector('script[src*="business-ai-widget.js"]');
    if (scriptTag) {
        widgetConfig.apiUrl = scriptTag.getAttribute('data-api-url') || widgetConfig.apiUrl;
        widgetConfig.widgetId = scriptTag.getAttribute('data-widget-id') || widgetConfig.widgetId;
        widgetConfig.position = scriptTag.getAttribute('data-position') || widgetConfig.position;
        widgetConfig.primaryColor = scriptTag.getAttribute('data-primary-color') || widgetConfig.primaryColor;
        widgetConfig.welcomeMessage = scriptTag.getAttribute('data-welcome-message') || widgetConfig.welcomeMessage;
        widgetConfig.brandName = scriptTag.getAttribute('data-brand-name') || widgetConfig.brandName;
        widgetConfig.language = scriptTag.getAttribute('data-language') || widgetConfig.language;
    }
    
    if (!widgetConfig.widgetId) {
        console.error('Business AI Widget: data-widget-id is required');
        return;
    }
    
    // Estado del widget
    const state = {
        isOpen: false,
        sessionId: generateSessionId(),
        userId: generateUserId(),
        messages: [],
        isLoading: false,
        cart: [],
        userProfile: null
    };
    
    // Generar ID de sesión único
    function generateSessionId() {
        let sessionId = sessionStorage.getItem('business_ai_session_id');
        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('business_ai_session_id', sessionId);
        }
        return sessionId;
    }
    
    // Generar ID de usuario único (persistente)
    function generateUserId() {
        let userId = localStorage.getItem('business_ai_user_id');
        if (!userId) {
            userId = 'user_' + Math.random().toString(36).substr(2, 12);
            localStorage.setItem('business_ai_user_id', userId);
        }
        return userId;
    }
    
    // Detectar información del usuario desde la página (pixel tracking)
    function detectUserContext() {
        return {
            pageUrl: window.location.href,
            pageTitle: document.title,
            referrer: document.referrer,
            userAgent: navigator.userAgent,
            language: navigator.language,
            timestamp: new Date().toISOString()
        };
    }
    
    // Crear HTML del widget
    function createWidgetHTML() {
        const positionClass = widgetConfig.position === 'bottom-left' ? 'left' : 'right';
        
        const widgetHTML = `
            <div id="business-ai-widget-container" class="business-ai-widget-${positionClass}">
                <!-- Botón flotante -->
                <div id="business-ai-widget-button" class="business-ai-widget-btn" role="button" tabindex="0" aria-label="Abrir chat">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2Z" fill="currentColor"/>
                    </svg>
                    <span class="business-ai-widget-badge" id="business-ai-widget-badge" style="display: none;">0</span>
                </div>
                
                <!-- Ventana de chat -->
                <div id="business-ai-widget-window" class="business-ai-widget-window" style="display: none;">
                    <!-- Header -->
                    <div class="business-ai-widget-header">
                        <div class="business-ai-widget-header-content">
                            <div class="business-ai-widget-avatar">🤖</div>
                            <div>
                                <div class="business-ai-widget-title">${widgetConfig.brandName}</div>
                                <div class="business-ai-widget-status">En línea • 24/7</div>
                            </div>
                        </div>
                        <button id="business-ai-widget-close" class="business-ai-widget-close" aria-label="Cerrar chat">×</button>
                    </div>
                    
                    <!-- Mensajes -->
                    <div id="business-ai-widget-messages" class="business-ai-widget-messages">
                        <div class="business-ai-widget-welcome">
                            ${widgetConfig.welcomeMessage}
                        </div>
                    </div>
                    
                    <!-- Input -->
                    <div class="business-ai-widget-input-container">
                        <input 
                            type="text" 
                            id="business-ai-widget-input" 
                            class="business-ai-widget-input" 
                            placeholder="Escribe tu mensaje..."
                            autocomplete="off"
                        />
                        <button id="business-ai-widget-send" class="business-ai-widget-send" aria-label="Enviar">
                            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                                <path d="M18 2L9 11M18 2L12 18L9 11M18 2L2 8L9 11" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', widgetHTML);
    }
    
    // Crear estilos CSS
    function createWidgetStyles() {
        const primaryColor = widgetConfig.primaryColor || '#007bff';
        const position = widgetConfig.position === 'bottom-left' ? 'left: 20px;' : 'right: 20px;';
        
        const styles = `
            <style id="business-ai-widget-styles">
                .business-ai-widget-right {
                    position: fixed;
                    bottom: 20px;
                    ${position}
                    z-index: 999999;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                }
                
                .business-ai-widget-left {
                    position: fixed;
                    bottom: 20px;
                    left: 20px;
                    z-index: 999999;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                }
                
                .business-ai-widget-btn {
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
                
                .business-ai-widget-btn:hover {
                    transform: scale(1.1);
                    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
                }
                
                .business-ai-widget-badge {
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
                
                .business-ai-widget-window {
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
                
                .business-ai-widget-header {
                    background: ${primaryColor};
                    color: white;
                    padding: 16px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                
                .business-ai-widget-header-content {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }
                
                .business-ai-widget-avatar {
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.2);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 20px;
                }
                
                .business-ai-widget-title {
                    font-weight: 600;
                    font-size: 16px;
                }
                
                .business-ai-widget-status {
                    font-size: 12px;
                    opacity: 0.9;
                }
                
                .business-ai-widget-close {
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
                
                .business-ai-widget-close:hover {
                    background: rgba(255, 255, 255, 0.2);
                }
                
                .business-ai-widget-messages {
                    flex: 1;
                    overflow-y: auto;
                    padding: 16px;
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                    background: #f5f5f5;
                }
                
                .business-ai-widget-welcome {
                    background: white;
                    padding: 12px 16px;
                    border-radius: 12px;
                    margin-bottom: 8px;
                    font-size: 14px;
                    line-height: 1.5;
                }
                
                .business-ai-widget-message {
                    max-width: 80%;
                    padding: 12px 16px;
                    border-radius: 12px;
                    font-size: 14px;
                    line-height: 1.5;
                    word-wrap: break-word;
                }
                
                .business-ai-widget-message.user {
                    background: ${primaryColor};
                    color: white;
                    align-self: flex-end;
                    border-bottom-right-radius: 4px;
                }
                
                .business-ai-widget-message.assistant {
                    background: white;
                    color: #333;
                    align-self: flex-start;
                    border-bottom-left-radius: 4px;
                    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
                }
                
                .business-ai-widget-message.loading {
                    background: white;
                    align-self: flex-start;
                    padding: 16px;
                }
                
                .business-ai-widget-loading-dots {
                    display: inline-flex;
                    gap: 4px;
                }
                
                .business-ai-widget-loading-dot {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: #ccc;
                    animation: business-ai-widget-bounce 1.4s infinite ease-in-out both;
                }
                
                .business-ai-widget-loading-dot:nth-child(1) { animation-delay: -0.32s; }
                .business-ai-widget-loading-dot:nth-child(2) { animation-delay: -0.16s; }
                
                @keyframes business-ai-widget-bounce {
                    0%, 80%, 100% { transform: scale(0); }
                    40% { transform: scale(1); }
                }
                
                .business-ai-widget-input-container {
                    display: flex;
                    padding: 12px;
                    background: white;
                    border-top: 1px solid #e0e0e0;
                    gap: 8px;
                }
                
                .business-ai-widget-input {
                    flex: 1;
                    border: 1px solid #e0e0e0;
                    border-radius: 20px;
                    padding: 10px 16px;
                    font-size: 14px;
                    outline: none;
                    transition: border-color 0.2s;
                }
                
                .business-ai-widget-input:focus {
                    border-color: ${primaryColor};
                }
                
                .business-ai-widget-send {
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
                
                .business-ai-widget-send:hover {
                    opacity: 0.9;
                }
                
                .business-ai-widget-send:disabled {
                    background: #ccc;
                    cursor: not-allowed;
                }
                
                .business-ai-widget-product-card {
                    background: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 12px;
                    margin: 8px 0;
                    cursor: pointer;
                    transition: box-shadow 0.2s;
                }
                
                .business-ai-widget-product-card:hover {
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                }
                
                .business-ai-widget-product-name {
                    font-weight: 600;
                    font-size: 14px;
                    margin-bottom: 4px;
                }
                
                .business-ai-widget-product-price {
                    color: ${primaryColor};
                    font-weight: 600;
                    font-size: 16px;
                }
                
                .business-ai-widget-cart-badge {
                    position: absolute;
                    top: -8px;
                    right: -8px;
                    background: #ff4444;
                    color: white;
                    border-radius: 50%;
                    width: 20px;
                    height: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 11px;
                    font-weight: bold;
                }
                
                @media (max-width: 480px) {
                    .business-ai-widget-window {
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
    
    // Enviar mensaje al backend (Business AI Omnicanal)
    async function sendMessage(message) {
        if (!message.trim() || state.isLoading) return;
        
        state.isLoading = true;
        
        // Agregar mensaje del usuario a la UI
        addMessageToUI('user', message);
        state.messages.push({ role: 'user', content: message });
        
        // Mostrar indicador de carga
        const loadingId = addLoadingMessage();
        
        try {
            // Obtener contexto del usuario (pixel tracking)
            const userContext = detectUserContext();
            
            // Preparar payload para Business AI Omnicanal
            const payload = {
                session_id: state.sessionId,
                user_id: state.userId,
                message: message,
                channel: 'web',
                display_name: null,
                language: widgetConfig.language,
                metadata: {
                    widget_id: widgetConfig.widgetId,
                    page_url: userContext.pageUrl,
                    page_title: userContext.pageTitle,
                    referrer: userContext.referrer,
                    timestamp: userContext.timestamp
                }
            };
            
            const response = await fetch(`${widgetConfig.apiUrl}/business-ai/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Remover indicador de carga
            removeLoadingMessage(loadingId);
            
            // Procesar respuesta
            const responseText = data.text || data.response || 'Lo siento, no pude procesar tu mensaje.';
            
            // Si hay productos en la respuesta, mostrarlos como cards
            if (data.tools && data.tools.products && Array.isArray(data.tools.products) && data.tools.products.length > 0) {
                // Mostrar productos como cards interactivas
                addProductsToUI(data.tools.products);
                
                // También mostrar texto de respuesta
                if (responseText) {
                    addMessageToUI('assistant', responseText);
                }
            } else {
                addMessageToUI('assistant', responseText);
            }
            
            state.messages.push({ role: 'assistant', content: responseText });
            
            // Actualizar perfil de usuario si viene en la respuesta
            if (data.user_profile) {
                state.userProfile = data.user_profile;
            }
            
            // Manejar carrito si viene en la respuesta
            if (data.cart && Array.isArray(data.cart)) {
                state.cart = data.cart;
                updateCartBadge();
            } else if (data.tools && data.tools.cart) {
                const cartData = data.tools.cart;
                if (cartData.items && Array.isArray(cartData.items)) {
                    state.cart = cartData.items;
                    updateCartBadge();
                }
            }
            
            // Manejar productos de cross-selling
            if (data.tools && data.tools.cross_sell_products && Array.isArray(data.tools.cross_sell_products)) {
                addMessageToUI('assistant', '💡 **También te podría interesar:**');
                addProductsToUI(data.tools.cross_sell_products);
            }
            
            // Manejar handoff humano
            if (data.needs_handoff) {
                addMessageToUI('assistant', '🔗 Te estoy conectando con un agente humano. Por favor espera un momento...');
            }
            
        } catch (error) {
            console.error('Error sending message:', error);
            removeLoadingMessage(loadingId);
            addMessageToUI('assistant', '⚠️ Lo siento, hubo un error de conexión. Por favor intenta de nuevo.');
        } finally {
            state.isLoading = false;
        }
    }
    
    // Agregar mensaje a la UI
    function addMessageToUI(role, content) {
        const messagesContainer = document.getElementById('business-ai-widget-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `business-ai-widget-message ${role}`;
        
        // Si es HTML, usar innerHTML; si no, textContent
        if (content.includes('<') || content.includes('**')) {
            // Convertir markdown básico a HTML
            let htmlContent = content
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/\n/g, '<br>');
            messageDiv.innerHTML = htmlContent;
        } else {
            messageDiv.textContent = content;
        }
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    // Agregar productos como cards (cross-selling y recomendaciones)
    function addProductsToUI(products) {
        const messagesContainer = document.getElementById('business-ai-widget-messages');
        const productsContainer = document.createElement('div');
        productsContainer.className = 'business-ai-widget-message assistant';
        
        products.forEach(product => {
            const productData = product.product || product; // Manejar diferentes formatos
            const productCard = document.createElement('div');
            productCard.className = 'business-ai-widget-product-card';
            
            const productName = productData.name || productData.product_name || productData.title || 'Producto';
            const productPrice = productData.price || productData.product_price || productData.cost || '0.00';
            const productId = productData.product_id || productData.id || '';
            
            productCard.innerHTML = `
                <div class="business-ai-widget-product-name">${productName}</div>
                <div class="business-ai-widget-product-price">$${parseFloat(productPrice).toFixed(2)}</div>
            `;
            
            // Click para agregar al carrito
            productCard.onclick = () => {
                if (productId) {
                    sendMessage(`Quiero agregar ${productName} al carrito`);
                } else {
                    sendMessage(`Quiero comprar ${productName}`);
                }
            };
            
            productsContainer.appendChild(productCard);
        });
        
        messagesContainer.appendChild(productsContainer);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    // Agregar indicador de carga
    function addLoadingMessage() {
        const messagesContainer = document.getElementById('business-ai-widget-messages');
        const loadingDiv = document.createElement('div');
        const loadingId = 'loading-' + Date.now();
        loadingDiv.id = loadingId;
        loadingDiv.className = 'business-ai-widget-message loading';
        loadingDiv.innerHTML = '<div class="business-ai-widget-loading-dots"><div class="business-ai-widget-loading-dot"></div><div class="business-ai-widget-loading-dot"></div><div class="business-ai-widget-loading-dot"></div></div>';
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
    
    // Actualizar badge del carrito
    function updateCartBadge() {
        const badge = document.getElementById('business-ai-widget-badge');
        if (state.cart && state.cart.length > 0) {
            badge.textContent = state.cart.length;
            badge.style.display = 'flex';
        } else {
            badge.style.display = 'none';
        }
    }
    
    // Toggle widget
    function toggleWidget() {
        state.isOpen = !state.isOpen;
        const window = document.getElementById('business-ai-widget-window');
        const button = document.getElementById('business-ai-widget-button');
        
        if (state.isOpen) {
            window.style.display = 'flex';
            button.style.display = 'none';
            setTimeout(() => {
                document.getElementById('business-ai-widget-input').focus();
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
        document.getElementById('business-ai-widget-button').addEventListener('click', toggleWidget);
        document.getElementById('business-ai-widget-close').addEventListener('click', toggleWidget);
        
        const input = document.getElementById('business-ai-widget-input');
        const sendBtn = document.getElementById('business-ai-widget-send');
        
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
        
        // Soporte para imágenes (drag & drop o input file)
        const inputElement = document.getElementById('business-ai-widget-input');
        inputElement.addEventListener('paste', (e) => {
            const items = e.clipboardData?.items;
            if (items) {
                for (let i = 0; i < items.length; i++) {
                    if (items[i].type.indexOf('image') !== -1) {
                        const blob = items[i].getAsFile();
                        handleImageUpload(blob);
                        e.preventDefault();
                        break;
                    }
                }
            }
        });
    }
    
    // Manejar subida de imágenes (para procesamiento con visión)
    async function handleImageUpload(blob) {
        // Convertir a base64 y enviar como mensaje especial
        const reader = new FileReader();
        reader.onloadend = () => {
            const base64Image = reader.result;
            sendMessage(`[Image] ${base64Image}`);
        };
        reader.readAsDataURL(blob);
    }
    
    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWidget);
    } else {
        initWidget();
    }
    
})();














