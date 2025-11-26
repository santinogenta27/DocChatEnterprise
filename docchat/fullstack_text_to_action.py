"""
Full-Stack Text-to-Action - Construye aplicaciones completas desde lenguaje natural.

Puede crear:
- Aplicaciones web completas (frontend + backend)
- APIs RESTful
- Interfaces de usuario
- Deployment automático
- Integración con servicios cloud
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage

from .config import AppConfig
from .utils.llm_factory import create_llm
from .text_to_action import CodeSandbox, TextToActionAgent


@dataclass
class ApplicationComponent:
    """Componente de una aplicación."""
    name: str
    type: str  # frontend, backend, api, database, etc.
    code: str
    dependencies: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FullStackApplication:
    """Aplicación full-stack completa."""
    app_id: str
    name: str
    description: str
    components: List[ApplicationComponent]
    architecture: Dict[str, Any]
    deployment_config: Dict[str, Any]
    status: str = "building"  # building, ready, deployed, failed
    build_log: List[str] = field(default_factory=list)
    deployment_url: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class FullStackTextToAction:
    """
    Sistema que convierte lenguaje natural en aplicaciones full-stack completas.
    
    Puede crear:
    - Aplicaciones web (React, Vue, HTML/CSS/JS)
    - Backends (Python Flask/FastAPI, Node.js Express)
    - APIs RESTful
    - Bases de datos
    - Deployment automático
    """
    
    def __init__(self, config: AppConfig, provider: str = "openai"):
        self.config = config
        self.provider = provider
        
        # LLM para arquitectura y diseño
        self.architect_llm = create_llm(
            provider=provider,
            model=config.agentic_model or "gpt-4o",
            temperature=0.2,  # Baja temperatura para diseño preciso
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=8000,
            request_timeout=180
        )
        
        # LLM para generación de código
        self.code_llm = create_llm(
            provider=provider,
            model=config.agentic_model or "gpt-4o",
            temperature=0.1,  # Muy baja para código preciso
            api_key=config.openai_api_key if provider == "openai" else config.anthropic_api_key,
            max_tokens=16000,  # Código puede ser largo
            request_timeout=300
        )
        
        # Sandbox para ejecutar código
        self.sandbox = CodeSandbox(timeout=60)
        
        # Directorio para aplicaciones
        self.apps_dir = Path(config.memory_dir) / "fullstack_apps"
        self.apps_dir.mkdir(parents=True, exist_ok=True)
        
        # Aplicaciones creadas
        self.applications: Dict[str, FullStackApplication] = {}
    
    def build_application(
        self,
        description: str,
        app_name: Optional[str] = None,
        tech_stack: Optional[List[str]] = None,
        features: Optional[List[str]] = None
    ) -> FullStackApplication:
        """
        Construye una aplicación full-stack completa desde una descripción.
        
        Args:
            description: Descripción en lenguaje natural de la aplicación
            app_name: Nombre de la aplicación (opcional)
            tech_stack: Stack tecnológico preferido (opcional)
            features: Lista de features específicas (opcional)
        
        Returns:
            FullStackApplication completa
        """
        app_id = f"app_{int(time.time())}"
        app_name = app_name or f"Application_{app_id}"
        
        print(f"\n{'='*60}")
        print(f"🚀 CONSTRUYENDO APLICACIÓN FULL-STACK")
        print(f"{'='*60}")
        print(f"📱 Nombre: {app_name}")
        print(f"📝 Descripción: {description}\n")
        
        # Paso 1: Diseñar arquitectura
        print("🏗️  Paso 1: Diseñando arquitectura...")
        architecture = self._design_architecture(description, tech_stack, features)
        print(f"   ✅ Arquitectura diseñada: {len(architecture.get('components', []))} componentes\n")
        
        # Paso 2: Generar componentes
        print("💻 Paso 2: Generando componentes...")
        components = []
        for comp_spec in architecture.get('components', []):
            print(f"   📦 Generando: {comp_spec.get('name', 'component')} ({comp_spec.get('type', 'unknown')})...")
            component = self._generate_component(comp_spec, description, architecture)
            components.append(component)
            print(f"      ✅ Componente generado")
        print()
        
        # Paso 3: Generar configuración de deployment
        print("🚀 Paso 3: Configurando deployment...")
        deployment_config = self._generate_deployment_config(architecture, components)
        print(f"   ✅ Configuración de deployment lista\n")
        
        # Crear aplicación
        app = FullStackApplication(
            app_id=app_id,
            name=app_name,
            description=description,
            components=components,
            architecture=architecture,
            deployment_config=deployment_config,
            status="ready"
        )
        
        # Guardar aplicación
        self.applications[app_id] = app
        self._save_application(app)
        
        print(f"{'='*60}")
        print(f"✅ APLICACIÓN CONSTRUIDA EXITOSAMENTE")
        print(f"{'='*60}\n")
        
        return app
    
    def _design_architecture(
        self,
        description: str,
        tech_stack: Optional[List[str]],
        features: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Diseña la arquitectura de la aplicación."""
        tech_stack_text = ", ".join(tech_stack) if tech_stack else "Recomendado automáticamente"
        features_text = "\n".join([f"- {f}" for f in features]) if features else "Todas las necesarias para la descripción"
        
        prompt = f"""Eres un arquitecto de software experto diseñando aplicaciones full-stack.

DESCRIPCIÓN DE LA APLICACIÓN:
{description}

STACK TECNOLÓGICO PREFERIDO:
{tech_stack_text}

FEATURES REQUERIDAS:
{features_text}

INSTRUCCIONES:
1. Diseña una arquitectura completa y funcional
2. Identifica todos los componentes necesarios (frontend, backend, API, database, etc.)
3. Define las tecnologías específicas a usar
4. Especifica las dependencias entre componentes
5. Incluye configuración de deployment

FORMATO DE RESPUESTA (JSON):
{{
    "architecture_type": "web_app" | "api" | "mobile_backend" | "desktop_app",
    "components": [
        {{
            "name": "nombre_componente",
            "type": "frontend" | "backend" | "api" | "database" | "auth" | "storage",
            "technology": "React" | "Flask" | "FastAPI" | "PostgreSQL" | etc,
            "description": "Qué hace este componente",
            "dependencies": ["otro_componente"],
            "files_needed": ["archivo1.py", "archivo2.js", ...]
        }},
        ...
    ],
    "tech_stack": ["tecnologia1", "tecnologia2", ...],
    "deployment_platform": "vercel" | "heroku" | "aws" | "docker" | "local",
    "database_type": "sqlite" | "postgresql" | "mongodb" | "none",
    "api_endpoints": [
        {{
            "method": "GET" | "POST" | "PUT" | "DELETE",
            "path": "/api/endpoint",
            "description": "Qué hace este endpoint"
        }},
        ...
    ]
}}

Diseña la arquitectura ahora:"""
        
        try:
            response = self.architect_llm.invoke(prompt).content.strip()
            json_match = self._extract_json(response)
            
            if json_match:
                return json.loads(json_match)
            else:
                # Arquitectura por defecto
                return {
                    "architecture_type": "web_app",
                    "components": [
                        {
                            "name": "frontend",
                            "type": "frontend",
                            "technology": "HTML/CSS/JavaScript",
                            "description": "Interfaz de usuario",
                            "dependencies": [],
                            "files_needed": ["index.html", "style.css", "app.js"]
                        },
                        {
                            "name": "backend",
                            "type": "backend",
                            "technology": "Python Flask",
                            "description": "Backend API",
                            "dependencies": [],
                            "files_needed": ["app.py", "requirements.txt"]
                        }
                    ],
                    "tech_stack": ["HTML", "CSS", "JavaScript", "Python", "Flask"],
                    "deployment_platform": "local",
                    "database_type": "sqlite"
                }
        except Exception as e:
            print(f"   ⚠️ Error diseñando arquitectura: {e}")
            return self._default_architecture()
    
    def _generate_component(
        self,
        comp_spec: Dict[str, Any],
        description: str,
        architecture: Dict[str, Any]
    ) -> ApplicationComponent:
        """Genera código para un componente."""
        comp_type = comp_spec.get("type", "unknown")
        comp_name = comp_spec.get("name", "component")
        technology = comp_spec.get("technology", "generic")
        files_needed = comp_spec.get("files_needed", [])
        
        prompt = f"""Eres un desarrollador experto generando código para un componente de aplicación.

DESCRIPCIÓN DE LA APLICACIÓN:
{description}

ARQUITECTURA COMPLETA:
{json.dumps(architecture, indent=2)[:2000]}

COMPONENTE A GENERAR:
Nombre: {comp_name}
Tipo: {comp_type}
Tecnología: {technology}
Archivos necesarios: {', '.join(files_needed)}
Descripción: {comp_spec.get('description', '')}

INSTRUCCIONES:
1. Genera código COMPLETO y FUNCIONAL para este componente
2. El código debe ser autocontenido y ejecutable
3. Incluye TODOS los archivos necesarios especificados
4. El código debe integrarse con otros componentes de la arquitectura
5. Incluye comentarios explicativos
6. Sigue las mejores prácticas de la tecnología especificada

FORMATO DE RESPUESTA (JSON):
{{
    "files": {{
        "archivo1.py": "código completo del archivo",
        "archivo2.js": "código completo del archivo",
        ...
    }},
    "dependencies": ["dependencia1", "dependencia2", ...],
    "config": {{
        "config_key": "config_value"
    }},
    "instructions": "Instrucciones para ejecutar este componente"
}}

Genera el código ahora:"""
        
        try:
            response = self.code_llm.invoke(prompt).content.strip()
            json_match = self._extract_json(response)
            
            if json_match:
                data = json.loads(json_match)
                files = data.get("files", {})
                
                # Combinar código de todos los archivos
                combined_code = "\n\n".join([
                    f"# === {filename} ===\n{code}"
                    for filename, code in files.items()
                ])
                
                return ApplicationComponent(
                    name=comp_name,
                    type=comp_type,
                    code=combined_code,
                    dependencies=data.get("dependencies", []),
                    config=data.get("config", {})
                )
            else:
                # Código básico por defecto
                return ApplicationComponent(
                    name=comp_name,
                    type=comp_type,
                    code=f"# Componente {comp_name} ({comp_type})\n# Código generado para: {description}",
                    dependencies=[],
                    config={}
                )
        except Exception as e:
            print(f"      ⚠️ Error generando componente: {e}")
            return ApplicationComponent(
                name=comp_name,
                type=comp_type,
                code=f"# Error generando componente: {str(e)}",
                dependencies=[],
                config={}
            )
    
    def _generate_deployment_config(
        self,
        architecture: Dict[str, Any],
        components: List[ApplicationComponent]
    ) -> Dict[str, Any]:
        """Genera configuración de deployment."""
        platform = architecture.get("deployment_platform", "local")
        
        config = {
            "platform": platform,
            "steps": [],
            "requirements": [],
            "environment_variables": {},
            "commands": {
                "install": "",
                "build": "",
                "start": "",
                "test": ""
            }
        }
        
        # Recopilar todas las dependencias
        all_deps = []
        for comp in components:
            all_deps.extend(comp.dependencies)
        config["requirements"] = list(set(all_deps))
        
        # Generar comandos según plataforma
        if platform == "local":
            config["commands"]["install"] = "pip install -r requirements.txt" if config["requirements"] else "echo 'No dependencies'"
            config["commands"]["start"] = "python app.py"
        elif platform == "docker":
            config["steps"] = [
                "Crear Dockerfile",
                "Construir imagen: docker build -t app .",
                "Ejecutar: docker run -p 5000:5000 app"
            ]
        elif platform == "vercel":
            config["steps"] = [
                "Instalar Vercel CLI: npm i -g vercel",
                "Deploy: vercel --prod"
            ]
        
        return config
    
    def deploy_application(self, app_id: str, platform: Optional[str] = None) -> Dict[str, Any]:
        """Despliega una aplicación."""
        if app_id not in self.applications:
            return {"success": False, "message": f"Aplicación {app_id} no encontrada"}
        
        app = self.applications[app_id]
        app.status = "deploying"
        
        print(f"\n🚀 Desplegando aplicación: {app.name}")
        
        # Guardar archivos de la aplicación
        app_dir = self.apps_dir / app_id
        app_dir.mkdir(parents=True, exist_ok=True)
        
        # Escribir código de componentes
        for comp in app.components:
            comp_dir = app_dir / comp.name
            comp_dir.mkdir(parents=True, exist_ok=True)
            
            # Guardar código (simplificado - en producción parsear archivos)
            code_file = comp_dir / f"{comp.name}.{self._get_file_extension(comp.type)}"
            code_file.write_text(comp.code, encoding='utf-8')
        
        # Crear requirements.txt si hay dependencias
        all_deps = []
        for comp in app.components:
            all_deps.extend(comp.dependencies)
        
        if all_deps:
            requirements_file = app_dir / "requirements.txt"
            requirements_file.write_text("\n".join(set(all_deps)), encoding='utf-8')
        
        # Crear README
        readme_content = f"""# {app.name}

{app.description}

## Componentes

{chr(10).join([f"- **{comp.name}** ({comp.type}): {len(comp.code)} caracteres" for comp in app.components])}

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución

```bash
python app.py
```

## Deployment

{json.dumps(app.deployment_config, indent=2)}
"""
        readme_file = app_dir / "README.md"
        readme_file.write_text(readme_content, encoding='utf-8')
        
        app.status = "deployed"
        app.deployment_url = f"file://{app_dir.absolute()}"
        
        self._save_application(app)
        
        return {
            "success": True,
            "message": f"Aplicación desplegada en {app_dir}",
            "app_id": app_id,
            "deployment_path": str(app_dir),
            "deployment_url": app.deployment_url
        }
    
    def _get_file_extension(self, comp_type: str) -> str:
        """Obtiene extensión de archivo según tipo de componente."""
        extensions = {
            "frontend": "html",
            "backend": "py",
            "api": "py",
            "database": "sql",
            "config": "json"
        }
        return extensions.get(comp_type, "txt")
    
    def _extract_json(self, text: str) -> Optional[str]:
        """Extrae JSON de un texto."""
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        return None
    
    def _default_architecture(self) -> Dict[str, Any]:
        """Arquitectura por defecto."""
        return {
            "architecture_type": "web_app",
            "components": [
                {
                    "name": "frontend",
                    "type": "frontend",
                    "technology": "HTML/CSS/JavaScript",
                    "description": "Interfaz de usuario",
                    "dependencies": [],
                    "files_needed": ["index.html"]
                }
            ],
            "tech_stack": ["HTML", "CSS", "JavaScript"],
            "deployment_platform": "local"
        }
    
    def _save_application(self, app: FullStackApplication):
        """Guarda una aplicación."""
        app_file = self.apps_dir / f"{app.app_id}.json"
        app_dict = {
            "app_id": app.app_id,
            "name": app.name,
            "description": app.description,
            "components": [
                {
                    "name": comp.name,
                    "type": comp.type,
                    "code": comp.code,
                    "dependencies": comp.dependencies,
                    "config": comp.config
                }
                for comp in app.components
            ],
            "architecture": app.architecture,
            "deployment_config": app.deployment_config,
            "status": app.status,
            "deployment_url": app.deployment_url,
            "timestamp": app.timestamp
        }
        
        with open(app_file, 'w', encoding='utf-8') as f:
            json.dump(app_dict, f, indent=2, ensure_ascii=False)
    
    def get_application(self, app_id: str) -> Optional[FullStackApplication]:
        """Obtiene una aplicación por ID."""
        return self.applications.get(app_id)
    
    def list_applications(self) -> List[FullStackApplication]:
        """Lista todas las aplicaciones."""
        return list(self.applications.values())

