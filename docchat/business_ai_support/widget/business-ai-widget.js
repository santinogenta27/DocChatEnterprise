/**
 * Business AI Support Widget - Embeddable Chat Widget
 * 
 * Usage:
 * <script src="https://your-domain.com/widget/business-ai-widget.js"></script>
 * <script>
 *   BusinessAIWidget.init({
 *     apiUrl: 'https://your-domain.com',
 *     primaryColor: '#007bff',
 *     position: 'bottom-right',
 *     logo: 'https://your-domain.com/logo.png'
 *   });
 * </script>
 */

(function() {
  'use strict';

  // Default configuration
  const DEFAULT_CONFIG = {
    apiUrl: window.location.origin,
    apiEndpoint: '/business-ai-support/chat',
    primaryColor: '#007bff',
    secondaryColor: '#6c757d',
    position: 'bottom-right', // bottom-right, bottom-left, top-right, top-left
    logo: null,
    brandName: 'Business AI Support',
    welcomeMessage: '¡Hola! 👋 ¿En qué puedo ayudarte hoy?',
    placeholder: 'Escribe tu mensaje...',
    showBranding: true,
    zIndex: 9999,
    language: 'es'
  };

  // Widget state
  let config = {};
  let isOpen = false;
  let sessionId = null;
  let messageHistory = [];
  let isLoading = false;

  // Generate unique session ID
  function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  // Initialize session
  function initSession() {
    if (!sessionId) {
      sessionId = generateSessionId();
    }
  }

  // Create widget HTML structure
  function createWidgetHTML() {
    const widgetContainer = document.createElement('div');
    widgetContainer.id = 'business-ai-widget-container';
    widgetContainer.className = 'business-ai-widget-container';
    widgetContainer.style.cssText = `
      position: fixed;
      ${getPositionStyles()}
      z-index: ${config.zIndex};
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    `;

    // Chat button (always visible)
    const chatButton = document.createElement('div');
    chatButton.id = 'business-ai-chat-button';
    chatButton.className = 'business-ai-chat-button';
    chatButton.innerHTML = `
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
      </svg>
    `;
    chatButton.style.cssText = `
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: ${config.primaryColor};
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      transition: transform 0.2s, box-shadow 0.2s;
    `;
    chatButton.addEventListener('click', toggleWidget);
    chatButton.addEventListener('mouseenter', function() {
      this.style.transform = 'scale(1.1)';
      this.style.boxShadow = '0 6px 16px rgba(0,0,0,0.2)';
    });
    chatButton.addEventListener('mouseleave', function() {
      this.style.transform = 'scale(1)';
      this.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
    });

    // Chat window (hidden by default)
    const chatWindow = document.createElement('div');
    chatWindow.id = 'business-ai-chat-window';
    chatWindow.className = 'business-ai-chat-window';
    chatWindow.style.cssText = `
      display: none;
      width: 380px;
      max-width: calc(100vw - 20px);
      height: 600px;
      max-height: calc(100vh - 100px);
      background: white;
      border-radius: 12px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.2);
      flex-direction: column;
      overflow: hidden;
      position: absolute;
      bottom: 80px;
      ${getWindowPosition()}
    `;

    // Header
    const header = document.createElement('div');
    header.className = 'business-ai-header';
    header.style.cssText = `
      background: ${config.primaryColor};
      color: white;
      padding: 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-radius: 12px 12px 0 0;
    `;
    
    const headerLeft = document.createElement('div');
    headerLeft.style.cssText = 'display: flex; align-items: center; gap: 12px;';
    
    if (config.logo) {
      const logoImg = document.createElement('img');
      logoImg.src = config.logo;
      logoImg.alt = config.brandName;
      logoImg.style.cssText = 'width: 32px; height: 32px; border-radius: 50%; object-fit: cover;';
      headerLeft.appendChild(logoImg);
    }
    
    const headerText = document.createElement('div');
    headerText.innerHTML = `
      <div style="font-weight: 600; font-size: 16px;">${config.brandName}</div>
      <div style="font-size: 12px; opacity: 0.9;">En línea</div>
    `;
    headerLeft.appendChild(headerText);
    header.appendChild(headerLeft);

    const closeButton = document.createElement('button');
    closeButton.innerHTML = '×';
    closeButton.style.cssText = `
      background: none;
      border: none;
      color: white;
      font-size: 24px;
      cursor: pointer;
      padding: 0;
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
      transition: background 0.2s;
    `;
    closeButton.addEventListener('click', toggleWidget);
    closeButton.addEventListener('mouseenter', function() {
      this.style.background = 'rgba(255,255,255,0.2)';
    });
    closeButton.addEventListener('mouseleave', function() {
      this.style.background = 'none';
    });
    header.appendChild(closeButton);

    // Messages container
    const messagesContainer = document.createElement('div');
    messagesContainer.id = 'business-ai-messages';
    messagesContainer.className = 'business-ai-messages';
    messagesContainer.style.cssText = `
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      background: #f8f9fa;
      display: flex;
      flex-direction: column;
      gap: 12px;
    `;

    // Welcome message
    const welcomeMsg = document.createElement('div');
    welcomeMsg.className = 'business-ai-message business-ai-message-bot';
    welcomeMsg.innerHTML = `<div class="business-ai-message-content">${config.welcomeMessage}</div>`;
    messagesContainer.appendChild(welcomeMsg);

    // Input area
    const inputArea = document.createElement('div');
    inputArea.className = 'business-ai-input-area';
    inputArea.style.cssText = `
      padding: 16px;
      background: white;
      border-top: 1px solid #e9ecef;
      display: flex;
      gap: 8px;
      align-items: center;
    `;

    const input = document.createElement('input');
    input.type = 'text';
    input.id = 'business-ai-input';
    input.placeholder = config.placeholder;
    input.style.cssText = `
      flex: 1;
      padding: 12px 16px;
      border: 1px solid #e9ecef;
      border-radius: 24px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s;
    `;
    input.addEventListener('focus', function() {
      this.style.borderColor = config.primaryColor;
    });
    input.addEventListener('blur', function() {
      this.style.borderColor = '#e9ecef';
    });
    input.addEventListener('keypress', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    const sendButton = document.createElement('button');
    sendButton.id = 'business-ai-send-button';
    sendButton.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="22" y1="2" x2="11" y2="13"></line>
        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
      </svg>
    `;
    sendButton.style.cssText = `
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: ${config.primaryColor};
      color: white;
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.2s, transform 0.2s;
      flex-shrink: 0;
    `;
    sendButton.addEventListener('click', sendMessage);
    sendButton.addEventListener('mouseenter', function() {
      this.style.background = darkenColor(config.primaryColor, 10);
      this.style.transform = 'scale(1.05)';
    });
    sendButton.addEventListener('mouseleave', function() {
      this.style.background = config.primaryColor;
      this.style.transform = 'scale(1)';
    });

    inputArea.appendChild(input);
    inputArea.appendChild(sendButton);

    chatWindow.appendChild(header);
    chatWindow.appendChild(messagesContainer);
    chatWindow.appendChild(inputArea);

    widgetContainer.appendChild(chatButton);
    widgetContainer.appendChild(chatWindow);

    return widgetContainer;
  }

  // Get position styles for button
  function getPositionStyles() {
    const positions = {
      'bottom-right': 'bottom: 20px; right: 20px;',
      'bottom-left': 'bottom: 20px; left: 20px;',
      'top-right': 'top: 20px; right: 20px;',
      'top-left': 'top: 20px; left: 20px;'
    };
    return positions[config.position] || positions['bottom-right'];
  }

  // Get window position
  function getWindowPosition() {
    if (config.position.includes('right')) {
      return 'right: 0;';
    } else {
      return 'left: 0;';
    }
  }

  // Darken color helper
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

  // Toggle widget open/close
  function toggleWidget() {
    const chatWindow = document.getElementById('business-ai-chat-window');
    const chatButton = document.getElementById('business-ai-chat-button');
    
    isOpen = !isOpen;
    
    if (isOpen) {
      chatWindow.style.display = 'flex';
      chatButton.style.display = 'none';
      initSession();
      document.getElementById('business-ai-input').focus();
      scrollToBottom();
    } else {
      chatWindow.style.display = 'none';
      chatButton.style.display = 'flex';
    }
  }

  // Send message
  async function sendMessage() {
    const input = document.getElementById('business-ai-input');
    const message = input.value.trim();
    
    if (!message || isLoading) return;
    
    // Clear input
    input.value = '';
    
    // Add user message to UI
    addMessageToUI('user', message);
    
    // Show loading
    showLoading();
    isLoading = true;
    
    try {
      // Send to API
      const response = await fetch(config.apiUrl + config.apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          user_id: sessionId,
          message: message,
          channel: 'web'
        })
      });
      
      const data = await response.json();
      
      // Hide loading
      hideLoading();
      isLoading = false;
      
      // Add bot response to UI
      if (data.text) {
        addMessageToUI('bot', data.text);
      } else if (data.error) {
        addMessageToUI('bot', 'Lo siento, hubo un error procesando tu mensaje. Por favor intenta de nuevo.');
      }
      
      // Store in history
      messageHistory.push({ role: 'user', content: message });
      if (data.text) {
        messageHistory.push({ role: 'assistant', content: data.text });
      }
      
    } catch (error) {
      console.error('Error sending message:', error);
      hideLoading();
      isLoading = false;
      addMessageToUI('bot', 'Lo siento, hubo un error de conexión. Por favor intenta de nuevo.');
    }
  }

  // Add message to UI
  function addMessageToUI(role, content) {
    const messagesContainer = document.getElementById('business-ai-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `business-ai-message business-ai-message-${role}`;
    
    const messageContent = document.createElement('div');
    messageContent.className = 'business-ai-message-content';
    messageContent.textContent = content;
    
    // Style based on role
    if (role === 'user') {
      messageDiv.style.cssText = 'display: flex; justify-content: flex-end;';
      messageContent.style.cssText = `
        background: ${config.primaryColor};
        color: white;
        padding: 10px 16px;
        border-radius: 18px 18px 4px 18px;
        max-width: 80%;
        word-wrap: break-word;
        font-size: 14px;
        line-height: 1.4;
      `;
    } else {
      messageDiv.style.cssText = 'display: flex; justify-content: flex-start;';
      messageContent.style.cssText = `
        background: white;
        color: #333;
        padding: 10px 16px;
        border-radius: 18px 18px 18px 4px;
        max-width: 80%;
        word-wrap: break-word;
        font-size: 14px;
        line-height: 1.4;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
      `;
    }
    
    messageDiv.appendChild(messageContent);
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
  }

  // Show loading indicator
  function showLoading() {
    const messagesContainer = document.getElementById('business-ai-messages');
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'business-ai-loading';
    loadingDiv.className = 'business-ai-message business-ai-message-bot';
    loadingDiv.style.cssText = 'display: flex; justify-content: flex-start;';
    loadingDiv.innerHTML = `
      <div class="business-ai-message-content" style="
        background: white;
        padding: 10px 16px;
        border-radius: 18px 18px 18px 4px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
      ">
        <div style="display: flex; gap: 4px;">
          <div style="width: 8px; height: 8px; border-radius: 50%; background: #ccc; animation: bounce 1.4s infinite;"></div>
          <div style="width: 8px; height: 8px; border-radius: 50%; background: #ccc; animation: bounce 1.4s infinite 0.2s;"></div>
          <div style="width: 8px; height: 8px; border-radius: 50%; background: #ccc; animation: bounce 1.4s infinite 0.4s;"></div>
        </div>
      </div>
    `;
    messagesContainer.appendChild(loadingDiv);
    scrollToBottom();
  }

  // Hide loading indicator
  function hideLoading() {
    const loading = document.getElementById('business-ai-loading');
    if (loading) {
      loading.remove();
    }
  }

  // Scroll to bottom
  function scrollToBottom() {
    const messagesContainer = document.getElementById('business-ai-messages');
    setTimeout(() => {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }, 100);
  }

  // Add CSS animations
  function addStyles() {
    if (document.getElementById('business-ai-widget-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'business-ai-widget-styles';
    style.textContent = `
      @keyframes bounce {
        0%, 80%, 100% { transform: scale(0); }
        40% { transform: scale(1); }
      }
      
      @media (max-width: 480px) {
        #business-ai-chat-window {
          width: calc(100vw - 20px) !important;
          height: calc(100vh - 100px) !important;
          bottom: 80px !important;
          left: 10px !important;
          right: 10px !important;
        }
      }
    `;
    document.head.appendChild(style);
  }

  // Public API
  window.BusinessAIWidget = {
    init: function(userConfig) {
      // Merge user config with defaults
      config = Object.assign({}, DEFAULT_CONFIG, userConfig);
      
      // Validate API URL
      if (!config.apiUrl) {
        console.error('BusinessAIWidget: apiUrl is required');
        return;
      }
      
      // Add styles
      addStyles();
      
      // Create and append widget
      const widget = createWidgetHTML();
      document.body.appendChild(widget);
      
      // Initialize session
      initSession();
      
      console.log('BusinessAIWidget initialized');
    },
    
    open: function() {
      if (!isOpen) {
        toggleWidget();
      }
    },
    
    close: function() {
      if (isOpen) {
        toggleWidget();
      }
    },
    
    sendMessage: function(message) {
      const input = document.getElementById('business-ai-input');
      if (input) {
        input.value = message;
        sendMessage();
      }
    },
    
    getConfig: function() {
      return config;
    },
    
    getSessionId: function() {
      return sessionId;
    }
  };

  // Auto-initialize if data attributes are present
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      const script = document.querySelector('script[data-business-ai-widget]');
      if (script) {
        const apiUrl = script.getAttribute('data-api-url') || window.location.origin;
        const primaryColor = script.getAttribute('data-primary-color') || DEFAULT_CONFIG.primaryColor;
        const position = script.getAttribute('data-position') || DEFAULT_CONFIG.position;
        const logo = script.getAttribute('data-logo');
        const brandName = script.getAttribute('data-brand-name') || DEFAULT_CONFIG.brandName;
        
        window.BusinessAIWidget.init({
          apiUrl: apiUrl,
          primaryColor: primaryColor,
          position: position,
          logo: logo,
          brandName: brandName
        });
      }
    });
  } else {
    const script = document.querySelector('script[data-business-ai-widget]');
    if (script) {
      const apiUrl = script.getAttribute('data-api-url') || window.location.origin;
      const primaryColor = script.getAttribute('data-primary-color') || DEFAULT_CONFIG.primaryColor;
      const position = script.getAttribute('data-position') || DEFAULT_CONFIG.position;
      const logo = script.getAttribute('data-logo');
      const brandName = script.getAttribute('data-brand-name') || DEFAULT_CONFIG.brandName;
      
      window.BusinessAIWidget.init({
        apiUrl: apiUrl,
        primaryColor: primaryColor,
        position: position,
        logo: logo,
        brandName: brandName
      });
    }
  }

})();

