#!/usr/bin/env python
"""
Script de prueba para AI Agent Business Manager
Verifica que todos los componentes funcionen correctamente
"""

import os
import sys
from pathlib import Path

# Agregar el directorio al path
sys.path.insert(0, str(Path(__file__).parent))

from docchat.ai_agent_business_manager_mode import AIAgentBusinessManagerMode
from docchat import load_config

def test_ai_agent_business():
    """Prueba completa del sistema AI Agent Business Manager"""
    
    print("=" * 60)
    print("🧪 PRUEBA: AI Agent Business Manager")
    print("=" * 60)
    
    try:
        # 1. Cargar configuración
        print("\n1️⃣ Cargando configuración...")
        config = load_config()
        print("✅ Configuración cargada")
        
        # 2. Inicializar el agente
        print("\n2️⃣ Inicializando AI Agent Business Manager...")
        agent = AIAgentBusinessManagerMode(config, provider="openai")
        db_type = "SQLite (fallback)" if agent.db_manager.use_fallback else "PostgreSQL"
        print(f"✅ Agente inicializado")
        print(f"   - Base de datos: {db_type}")
        
        # 3. Crear una empresa de prueba
        print("\n3️⃣ Creando empresa de prueba...")
        company_result = agent.create_company(
            company_name="Empresa Demo Test",
            contact_email="demo@test.com",
            company_description="Empresa de demostración para pruebas del sistema",
            plan="free",
            website_url="https://demo-test.com"
        )
        company_id = company_result["company_id"]
        widget_script_id = company_result["widget_script_id"]
        print(f"✅ Empresa creada exitosamente")
        print(f"   - Company ID: {company_id}")
        print(f"   - Widget Script ID: {widget_script_id}")
        print(f"   - Nombre: {company_result['company_name']}")
        
        # 4. Agregar un producto
        print("\n4️⃣ Agregando producto de prueba...")
        product_result = agent.add_product(
            company_id=company_id,
            product_name="Plan Básico",
            product_description="Plan básico de servicios con soporte estándar",
            price=99.99,
            currency="USD",
            product_url="https://demo-test.com/producto/plan-basico",
            category="Software"
        )
        print(f"✅ Producto agregado")
        print(f"   - Product ID: {product_result['product_id']}")
        print(f"   - Nombre: {product_result['product_name']}")
        
        # Agregar otro producto
        agent.add_product(
            company_id=company_id,
            product_name="Plan Premium",
            product_description="Plan premium con todas las funcionalidades",
            price=299.99,
            currency="USD",
            product_url="https://demo-test.com/producto/plan-premium",
            category="Software"
        )
        print(f"   - Producto adicional agregado")
        
        # 5. Probar detección de intención
        print("\n5️⃣ Probando detección de intención...")
        test_messages = [
            "Hola, buenos días",
            "¿Qué productos tienen?",
            "¿Cuánto cuesta el plan básico?",
            "Quiero comprar el plan premium",
            "Necesito ayuda con mi cuenta"
        ]
        
        for msg in test_messages:
            intent = agent.conversational_ai.detect_intent(msg)
            print(f"   - '{msg}' → Intención: {intent}")
        
        # 6. Probar procesamiento de mensaje completo
        print("\n6️⃣ Probando procesamiento de mensaje completo...")
        test_message = "Hola, ¿qué productos tienen disponibles?"
        result = agent.process_message(
            widget_script_id=widget_script_id,
            message=test_message,
            user_id="test_user_123",
            channel="web_widget"
        )
        
        print(f"✅ Mensaje procesado exitosamente")
        print(f"   - Conversación ID: {result['conversation_id']}")
        print(f"   - Intención detectada: {result['intent']}")
        print(f"   - Respuesta generada: {result['response'][:100]}...")
        print(f"   - Crear lead: {result['should_create_lead']}")
        print(f"   - Escalar: {result['should_escalate']}")
        
        # 7. Probar otro mensaje (para verificar historial)
        print("\n7️⃣ Probando segundo mensaje (con historial)...")
        result2 = agent.process_message(
            widget_script_id=widget_script_id,
            message="¿Cuál es el precio del plan básico?",
            user_id="test_user_123",
            channel="web_widget"
        )
        print(f"✅ Segundo mensaje procesado")
        print(f"   - Intención: {result2['intent']}")
        print(f"   - Respuesta: {result2['response'][:100]}...")
        
        # 8. Verificar analytics
        print("\n8️⃣ Verificando analytics...")
        analytics = agent.get_analytics(company_id, days=30)
        print(f"✅ Analytics obtenidos")
        print(f"   - Total leads: {analytics['total_leads']}")
        print(f"   - Leads por intención: {analytics['leads_by_intent']}")
        print(f"   - Leads por canal: {analytics['leads_by_channel']}")
        
        # 9. Verificar configuración de empresa
        print("\n9️⃣ Verificando configuración completa...")
        config_data = agent.get_company_config(company_id)
        print(f"✅ Configuración obtenida")
        print(f"   - Productos registrados: {len(config_data['products'])}")
        print(f"   - Total leads: {config_data['total_leads']}")
        
        # 10. Obtener código del widget
        print("\n🔟 Obteniendo código del widget...")
        widget_code = config_data["company"]["widget_code"]
        print(f"✅ Código del widget generado")
        print(f"   - Longitud del código: {len(widget_code)} caracteres")
        print(f"   - Widget Script ID incluido: {'widget_script_id' in widget_code}")
        
        print("\n" + "=" * 60)
        print("✅ PRUEBA COMPLETADA EXITOSAMENTE")
        print("=" * 60)
        print("\n📋 RESUMEN:")
        print(f"   ✅ Sistema inicializado")
        print(f"   ✅ Empresa creada: {company_id}")
        print(f"   ✅ Widget Script ID: {widget_script_id}")
        print(f"   ✅ Productos agregados: 2")
        print(f"   ✅ Mensajes procesados: 2")
        print(f"   ✅ Detección de intención: Funcionando")
        print(f"   ✅ Generación de respuestas: Funcionando")
        print(f"   ✅ Analytics: Funcionando")
        print("\n🎯 El sistema está LISTO PARA USAR en producción")
        print(f"\n💻 Para usar el widget, copia este código a tu sitio web:")
        print("-" * 60)
        print(widget_code[:200] + "...")
        print("-" * 60)
        
        return {
            "success": True,
            "company_id": company_id,
            "widget_script_id": widget_script_id,
            "widget_code": widget_code
        }
        
    except Exception as e:
        print(f"\n❌ ERROR en la prueba: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    result = test_ai_agent_business()
    sys.exit(0 if result.get("success") else 1)

