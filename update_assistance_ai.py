"""Script para actualizar todas las referencias de Business AI a Assistance AI"""
import os
from pathlib import Path

def update_file(file_path: Path):
    """Actualiza referencias en un archivo"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        # Reemplazos de texto
        replacements = [
            # Imports y referencias de módulo
            ('business_ai_omnicanal', 'assistance_ai'),
            ('from .business_ai_mode', 'from .assistance_ai_mode'),
            ('from ..business_ai_omnicanal', 'from ..assistance_ai'),
            
            # Clases
            ('BusinessAIMode', 'AssistanceAIMode'),
            ('BusinessAIAgent', 'AssistanceAIAgent'),
            ('BusinessAIConfig', 'AssistanceAIConfig'),
            
            # Nombres y textos
            ('Business AI Omnicanal', 'Assistance AI'),
            ('Business AI', 'Assistance AI'),
            ('business_ai_mode', 'assistance_ai_mode'),
            ('business_ai_agent', 'assistance_ai_agent'),
            ('business_ai_config', 'assistance_ai_config'),
            
            # Mensajes y logs
            ('Business AI usando', 'Assistance AI usando'),
            ('Business AI inicializado', 'Assistance AI inicializado'),
            ('Business AI Chat', 'Assistance AI Chat'),
            ('Estadísticas - Business AI', 'Estadísticas - Assistance AI'),
            
            # Configuraciones específicas
            ('GROQ_API_KEY requerida para Business AI Omnicanal', 'GROQ_API_KEY requerida para Assistance AI'),
            ('SIEMPRE usar Groq para Business AI Omnicanal', 'SIEMPRE usar Groq para Assistance AI'),
            
            # Comentarios y docstrings
            ('Modo principal Business AI Omnicanal', 'Modo principal Assistance AI'),
            ('Agente unificado de ventas + soporte 24/7', 'Agente unificado de asistencia 24/7'),
        ]
        
        for old, new in replacements:
            content = content.replace(old, new)
        
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            return True
        return False
    except Exception as e:
        print(f"Error actualizando {file_path}: {e}")
        return False

def main():
    """Actualiza todos los archivos en assistance_ai"""
    base_path = Path(__file__).parent / 'docchat' / 'assistance_ai'
    
    if not base_path.exists():
        print(f"Error: Directorio no encontrado: {base_path}")
        return
    
    updated_count = 0
    total_files = 0
    
    # Recorrer todos los archivos .py
    for py_file in base_path.rglob('*.py'):
        total_files += 1
        if update_file(py_file):
            updated_count += 1
            print(f"Actualizado: {py_file.relative_to(base_path)}")
    
    print(f"\nProceso completado: {updated_count}/{total_files} archivos actualizados")

if __name__ == '__main__':
    main()

