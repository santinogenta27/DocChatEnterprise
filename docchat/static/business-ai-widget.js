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
        language: 'es',
        enableWhatsApp: false,
        enableMessenger: false,
        whatsappNumber: null,
        whatsappMessage: 'Hola, vi tu producto en tu website',
        messengerPage: null
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
        widgetConfig.enableWhatsApp = scriptTag.getAttribute('data-enable-whatsapp') === 'true' || scriptTag.getAttribute('data-enable-whatsapp') === '1';
        widgetConfig.enableMessenger = scriptTag.getAttribute('data-enable-messenger') === 'true' || scriptTag.getAttribute('data-enable-messenger') === '1';
        widgetConfig.whatsappNumber = scriptTag.getAttribute('data-whatsapp-number') || widgetConfig.whatsappNumber;
        widgetConfig.whatsappMessage = scriptTag.getAttribute('data-whatsapp-message') || widgetConfig.whatsappMessage;
        widgetConfig.messengerPage = scriptTag.getAttribute('data-messenger-page') || widgetConfig.messengerPage;
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
                        <div id="business-ai-widget-external-chat-buttons" class="business-ai-widget-external-chat-buttons" style="display: none;"></div>
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
                    color: #000000;
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
                
                .business-ai-widget-external-chat-buttons {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                    margin-top: 12px;
                    margin-bottom: 8px;
                }
                
                .business-ai-widget-external-btn {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    padding: 12px 16px;
                    border-radius: 8px;
                    border: 1px solid #e0e0e0;
                    background: white;
                    cursor: pointer;
                    transition: all 0.2s;
                    font-size: 14px;
                    font-weight: 500;
                    text-decoration: none;
                    color: #333;
                }
                
                .business-ai-widget-external-btn:hover {
                    background: #f5f5f5;
                    border-color: ${primaryColor};
                    transform: translateY(-1px);
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                }
                
                .business-ai-widget-external-btn.whatsapp {
                    border-color: #25D366;
                }
                
                .business-ai-widget-external-btn.whatsapp:hover {
                    background: #25D366;
                    color: white;
                    border-color: #25D366;
                }
                
                .business-ai-widget-external-btn.messenger {
                    border-color: #0084ff;
                }
                
                .business-ai-widget-external-btn.messenger:hover {
                    background: #0084ff;
                    color: white;
                    border-color: #0084ff;
                }
                
                .business-ai-widget-external-btn-icon {
                    font-size: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 20px;
                    height: 20px;
                    flex-shrink: 0;
                }
                
                .business-ai-widget-external-btn-icon svg {
                    width: 100%;
                    height: 100%;
                }
                
                .business-ai-widget-external-btn.whatsapp .business-ai-widget-external-btn-icon svg {
                    fill: #25D366;
                }
                
                .business-ai-widget-external-btn.whatsapp:hover .business-ai-widget-external-btn-icon svg {
                    fill: white;
                }
                
                .business-ai-widget-external-btn-text {
                    flex: 1;
                }
                
                .business-ai-widget-external-btn-arrow {
                    font-size: 12px;
                    opacity: 0.6;
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
            
            const response = await fetch(`${widgetConfig.apiUrl}/api/widget/chat`, {
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
    
    // Crear botones de WhatsApp y Messenger
    function createExternalChatButtons() {
        const buttonsContainer = document.getElementById('business-ai-widget-external-chat-buttons');
        if (!buttonsContainer) return;
        
        buttonsContainer.innerHTML = '';
        
        // Botón de WhatsApp
        if (widgetConfig.enableWhatsApp && widgetConfig.whatsappNumber) {
            const whatsappBtn = document.createElement('a');
            whatsappBtn.className = 'business-ai-widget-external-btn whatsapp';
            
            const phoneNumber = widgetConfig.whatsappNumber.replace(/[^0-9]/g, '');
            const encodedMessage = encodeURIComponent(widgetConfig.whatsappMessage);
            const whatsappUrl = `https://wa.me/${phoneNumber}?text=${encodedMessage}`;
            whatsappBtn.href = whatsappUrl;
            whatsappBtn.target = '_blank';
            whatsappBtn.rel = 'noopener noreferrer';
            
            whatsappBtn.innerHTML = `
                <span class="business-ai-widget-external-btn-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
                    </svg>
                </span>
                <span class="business-ai-widget-external-btn-text">Prefiero WhatsApp</span>
                <span class="business-ai-widget-external-btn-arrow">→</span>
            `;
            
            buttonsContainer.appendChild(whatsappBtn);
        }
        
        // Botón de Messenger
        if (widgetConfig.enableMessenger && widgetConfig.messengerPage) {
            const messengerBtn = document.createElement('a');
            messengerBtn.className = 'business-ai-widget-external-btn messenger';
            
            let messengerPage = widgetConfig.messengerPage.replace(/^@/, '').replace(/^https?:\/\/(www\.)?(facebook\.com|fb\.com)\//, '').replace(/\/$/, '');
            messengerBtn.href = `https://m.me/${messengerPage}`;
            messengerBtn.target = '_blank';
            messengerBtn.rel = 'noopener noreferrer';
            
            messengerBtn.innerHTML = `
                <span class="business-ai-widget-external-btn-icon">💙</span>
                <span class="business-ai-widget-external-btn-text">Prefiero Messenger</span>
                <span class="business-ai-widget-external-btn-arrow">→</span>
            `;
            
            buttonsContainer.appendChild(messengerBtn);
        }
        
        // Mostrar contenedor si hay botones
        if (buttonsContainer.children.length > 0) {
            buttonsContainer.style.display = 'flex';
        } else {
            buttonsContainer.style.display = 'none';
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
        
        // Crear botones de WhatsApp/Messenger
        createExternalChatButtons();
        
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














