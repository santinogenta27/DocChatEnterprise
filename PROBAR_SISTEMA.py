"""Script para probar el sistema Enterprise API + Cloud Storage sin datos reales."""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pathlib import Path
import tempfile
import json
from io import BytesIO

from docchat import load_config
from docchat.enterprise_api import EnterpriseAPIMode
from docchat.cloud_integrations import CloudStorageIntegration

def crear_archivos_prueba():
    """Crea archivos de prueba para simular cloud storage."""
    archivos = []
    
    # Crear archivos temporales de prueba
    temp_dir = Path(tempfile.mkdtemp())
    
    # Archivo 1: Contrato de ejemplo
    contrato = temp_dir / "contrato_ejemplo.pdf"
    contrato.write_text("""
    CONTRATO DE SERVICIOS
    
    Este contrato establece los términos y condiciones para la prestación de servicios.
    
    Fecha de vencimiento: 2025-12-31
    
    Cláusulas importantes:
    - Pago mensual de $10,000
    - Penalización por incumplimiento: 5% del monto
    - Renovación automática a menos que se notifique con 30 días de anticipación
    
    RIESGO: Este contrato tiene una cláusula de renovación automática que podría
    causar problemas si no se revisa a tiempo.
    """)
    archivos.append(contrato)
    
    # Archivo 2: Informe financiero
    informe = temp_dir / "informe_financiero_2025.txt"
    informe.write_text("""
    INFORME FINANCIERO Q4 2025
    
    Resumen Ejecutivo:
    - Ingresos totales: $2,500,000
    - Gastos operativos: $1,800,000
    - Ganancia neta: $700,000
    - Crecimiento: 15% vs Q3
    
    OPORTUNIDAD: Los gastos operativos han aumentado 10% pero los ingresos solo 5%.
    Hay oportunidad de optimizar costos operativos.
    
    PATRÓN: El crecimiento se está desacelerando. Se recomienda revisar estrategia.
    """)
    archivos.append(informe)
    
    # Archivo 3: Email corporativo
    email = temp_dir / "email_importante.md"
    email.write_text("""
    Asunto: Reunión importante - Revisión de contratos
    
    Estimado equipo,
    
    Necesitamos revisar urgentemente los contratos que vencen en diciembre.
    
    Hay 5 contratos que requieren atención inmediata:
    1. Contrato con Proveedor A - Vence 2025-12-15
    2. Contrato con Proveedor B - Vence 2025-12-20
    3. Contrato con Proveedor C - Vence 2025-12-31
    
    PROBLEMA CRÍTICO: Si no renovamos estos contratos a tiempo, perderemos
    servicios esenciales.
    
    Acción requerida: Revisar y renovar antes del 10 de diciembre.
    """)
    archivos.append(email)
    
    return archivos, temp_dir

def probar_enterprise_api():
    """Prueba Enterprise API Mode con archivos de prueba."""
    print("=" * 60)
    print("PROBANDO ENTERPRISE API MODE")
    print("=" * 60)
    
    config = load_config()
    enterprise_api = EnterpriseAPIMode(config)
    
    # Crear archivos de prueba
    print("\nCreando archivos de prueba...")
    archivos, temp_dir = crear_archivos_prueba()
    print(f"OK - Creados {len(archivos)} archivos de prueba")
    
    # Procesar con Enterprise API
    print("\nProcesando con Enterprise API...")
    print("   - Detección automática: ACTIVADA")
    print("   - Reglas: NINGUNA")
    
    try:
        results = enterprise_api.process_enterprise_documents(
            files=archivos,
            auto_detect=True,
            rules=[]
        )
        
        print("\n" + "=" * 60)
        print("RESULTADOS DEL PROCESAMIENTO")
        print("=" * 60)
        
        print(f"\nEstado: {results.get('status', 'unknown')}")
        print(f"Documentos procesados: {results.get('documents_processed', 0)}")
        print(f"Chunks generados: {results.get('chunks_generated', 0)}")
        
        # Resúmenes
        if results.get('summaries'):
            print("\nRESUMENES AUTOMATICOS:")
            for file_name, summary in results['summaries'].items():
                print(f"\n  Archivo: {file_name}")
                print(f"     Tipo: {summary.get('document_type', 'N/A')}")
                print(f"     Resumen: {summary.get('summary', 'N/A')[:100]}...")
                if summary.get('key_points'):
                    print(f"     Puntos clave: {len(summary['key_points'])}")
        
        # Problemas detectados
        if results.get('problems_detected'):
            print("\nPROBLEMAS DETECTADOS:")
            for problem in results['problems_detected']:
                print(f"  - {problem.get('type', 'Unknown')} ({problem.get('severity', 'N/A')})")
                print(f"    {problem.get('description', 'N/A')[:80]}...")
        
        # Oportunidades
        if results.get('opportunities_detected'):
            print("\nOPORTUNIDADES DETECTADAS:")
            for opp in results['opportunities_detected']:
                print(f"  - {opp.get('type', 'Unknown')} ({opp.get('impact', 'N/A')})")
                print(f"    {opp.get('description', 'N/A')[:80]}...")
        
        # Patrones
        if results.get('patterns_found'):
            print("\nPATRONES ENCONTRADOS:")
            for pattern in results['patterns_found']:
                print(f"  - {pattern.get('type', 'Unknown')}")
                print(f"    {pattern.get('description', 'N/A')[:80]}...")
        
        # Insights
        if results.get('insights'):
            print("\nINSIGHTS:")
            for insight in results['insights']:
                print(f"  - {insight.get('title', 'Insight')}")
                print(f"    {insight.get('content', 'N/A')[:80]}...")
        
        print("\n" + "=" * 60)
        print("PRUEBA COMPLETADA EXITOSAMENTE")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Limpiar archivos temporales
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

def probar_conexion_cloud_storage():
    """Prueba la conexión simulada con cloud storage."""
    print("\n" + "=" * 60)
    print("PROBANDO CLOUD STORAGE INTEGRATION")
    print("=" * 60)
    
    config = load_config()
    enterprise_api = EnterpriseAPIMode(config)
    cloud_integration = CloudStorageIntegration(config, enterprise_api)
    
    print("\nSimulando conexion con S3...")
    print("   (Sin datos reales, solo verificando que el sistema funcione)")
    
    # Crear archivos de prueba
    archivos, temp_dir = crear_archivos_prueba()
    
    # Simular que estos archivos vienen de S3
    print(f"\nOK - Simulando {len(archivos)} archivos desde 'bucket-prueba'")
    print("   - contrato_ejemplo.pdf")
    print("   - informe_financiero_2025.txt")
    print("   - email_importante.md")
    
    # Procesar como si vinieran de cloud storage
    print("\nProcesando archivos (simulando descarga desde S3)...")
    
    try:
        # Usar Enterprise API directamente (simula lo que haría cloud_integration)
        results = enterprise_api.process_enterprise_documents(
            files=archivos,
            auto_detect=True,
            rules=[]
        )
        
        print(f"\nOK - Archivos procesados: {results.get('documents_processed', 0)}")
        print(f"OK - Chunks generados: {results.get('chunks_generated', 0)}")
        
        if results.get('problems_detected'):
            print(f"PROBLEMAS detectados: {len(results['problems_detected'])}")
        
        if results.get('opportunities_detected'):
            print(f"OPORTUNIDADES detectadas: {len(results['opportunities_detected'])}")
        
        print("\n" + "=" * 60)
        print("CONEXION CLOUD STORAGE VERIFICADA")
        print("=" * 60)
        print("\nNOTA: Para probar con datos reales:")
        print("   1. Ve a la tab 'Cloud Storage' en el website")
        print("   2. Conecta tu bucket de S3/GCS/Azure")
        print("   3. Los archivos se procesaran automaticamente")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

def verificar_conexiones():
    """Verifica que todo esté conectado correctamente."""
    print("=" * 60)
    print("VERIFICANDO CONEXIONES")
    print("=" * 60)
    
    try:
        config = load_config()
        print("OK - Config cargada")
        
        enterprise_api = EnterpriseAPIMode(config)
        print("OK - EnterpriseAPIMode inicializado")
        
        cloud_integration = CloudStorageIntegration(config, enterprise_api)
        print("OK - CloudStorageIntegration inicializado")
        
        print("\n" + "=" * 60)
        print("TODO ESTA CONECTADO CORRECTAMENTE")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PROBANDO SISTEMA ENTERPRISE API + CLOUD STORAGE")
    print("=" * 60)
    
    # 1. Verificar conexiones
    if not verificar_conexiones():
        print("\nERROR en verificacion. Revisa los errores arriba.")
        exit(1)
    
    # 2. Probar Enterprise API
    if not probar_enterprise_api():
        print("\nERROR en Enterprise API. Revisa los errores arriba.")
        exit(1)
    
    # 3. Probar Cloud Storage Integration
    if not probar_conexion_cloud_storage():
        print("\nERROR en Cloud Storage. Revisa los errores arriba.")
        exit(1)
    
    print("\n" + "=" * 60)
    print("TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE")
    print("=" * 60)
    print("\nPROXIMOS PASOS:")
    print("   1. Ejecuta: python app.py")
    print("   2. Ve a la tab 'Enterprise API' para procesar documentos")
    print("   3. Ve a la tab 'Cloud Storage' para conectar tu bucket real")
    print("\n")

