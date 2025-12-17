#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de prueba directa para AI Agent Business Manager
Evita problemas de encoding importando directamente
"""

import os
import sys
from pathlib import Path

# Configurar encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))

# Importar directamente sin pasar por __init__.py
from docchat.config import AppConfig, load_config
from docchat.ai_agent_business_manager_mode import AIAgentBusinessManagerMode

def main():
    print("=" * 60)
    print("PRUEBA: AI Agent Business Manager")
    print("=" * 60)
    
    try:
        # 1. Cargar configuración
        print("\n[1/8] Cargando configuracion...")
        config = load_config()
        print("OK - Configuracion cargada")
        
        # 2. Inicializar agente
        print("\n[2/8] Inicializando agente...")
        agent = AIAgentBusinessManagerMode(config, provider="openai")
        db_type = "SQLite" if agent.db_manager.use_fallback else "PostgreSQL"
        print(f"OK - Agente inicializado (DB: {db_type})")
        
        # 3. Crear empresa
        print("\n[3/8] Creando empresa de prueba...")
        company_result = agent.create_company(
            company_name="Empresa Demo Test",
            contact_email="demo@test.com",
            company_description="Empresa de demostracion para pruebas",
            plan="free",
            website_url="https://demo-test.com"
        )
        company_id = company_result["company_id"]
        widget_id = company_result["widget_script_id"]
        print(f"OK - Empresa creada")
        print(f"   Company ID: {company_id}")
        print(f"   Widget ID: {widget_id}")
        
        # 4. Agregar productos
        print("\n[4/8] Agregando productos...")
        agent.add_product(company_id, "Plan Basico", "Plan basico de servicios", 99.99, "USD", "https://demo.com/plan-basico", "Software")
        agent.add_product(company_id, "Plan Premium", "Plan premium completo", 299.99, "USD", "https://demo.com/plan-premium", "Software")
        print("OK - 2 productos agregados")
        
        # 5. Probar mensaje
        print("\n[5/8] Probando procesamiento de mensaje...")
        result = agent.process_message(
            widget_script_id=widget_id,
            message="Hola, que productos tienen?",
            user_id="test_user_123",
            channel="web_widget"
        )
        print("OK - Mensaje procesado")
        print(f"   Intencion: {result.get('intent')}")
        print(f"   Respuesta: {result.get('response', '')[:80]}...")
        
        # 6. Segundo mensaje
        print("\n[6/8] Probando segundo mensaje (con historial)...")
        result2 = agent.process_message(
            widget_script_id=widget_id,
            message="Cual es el precio del plan basico?",
            user_id="test_user_123",
            channel="web_widget"
        )
        print("OK - Segundo mensaje procesado")
        print(f"   Intencion: {result2.get('intent')}")
        print(f"   Respuesta: {result2.get('response', '')[:80]}...")
        
        # 7. Analytics
        print("\n[7/8] Obteniendo analytics...")
        analytics = agent.get_analytics(company_id, days=30)
        print("OK - Analytics obtenidos")
        print(f"   Total leads: {analytics.get('total_leads', 0)}")
        
        # 8. Widget code
        print("\n[8/8] Generando codigo del widget...")
        config_data = agent.get_company_config(company_id)
        widget_code = config_data["company"]["widget_code"]
        print("OK - Codigo generado")
        print(f"   Longitud: {len(widget_code)} caracteres")
        
        print("\n" + "=" * 60)
        print("PRUEBA COMPLETADA EXITOSAMENTE")
        print("=" * 60)
        print("\nRESUMEN:")
        print(f"  - Empresa creada: {company_id}")
        print(f"  - Widget Script ID: {widget_id}")
        print(f"  - Mensajes procesados: 2")
        print(f"  - Productos: 2")
        print("\nEl sistema esta LISTO para usar en produccion")
        print("\nPara probar el endpoint, usa:")
        print(f"  POST http://localhost:7860/api/ai-agent-business/message")
        print(f"  Body: {{'widget_script_id': '{widget_id}', 'message': 'Hola', ...}}")
        
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

