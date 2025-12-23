"""
Código para agregar el tab de Advertising Top Manager en app.py
Este código debe agregarse donde se crean los tabs de Gradio
"""
# ========== ADVERTISING TOP MANAGER TAB ==========
# Agregar este código donde se crean los tabs de Gradio (probablemente cerca del final de app.py)
# Buscar algo como: "with gr.Tab(" o "demo = gr.Blocks(...)" y agregar este código dentro

advertising_top_manager_tab_code = """
        # Tab: 📈 Advertising Top Manager - Publicación Automática de Anuncios
        with gr.Tab("📈 Advertising Top Manager"):
            gr.Markdown("""
            # 📈 Advertising Top Manager
            
            ## 🚀 Crea y Publica Anuncios Automáticamente en Meta y Google Ads
            
            **Características:**
            - ✅ Publicación automática en Meta (Facebook/Instagram) y Google Ads
            - ✅ IA genera copy y variaciones automáticamente
            - ✅ Análisis de imágenes/videos con visión computacional
            - ✅ Optimización automática de campañas
            - ✅ Multi-platform (Meta + Google en un solo lugar)
            
            **Para usar:**
            1. Sube imágenes o videos de tu producto
            2. Configura nombre, presupuesto y objetivo
            3. Selecciona plataformas (Meta, Google, o ambas)
            4. Marca "Publicar Automáticamente" si quieres que se publiquen como ACTIVE
            5. Click en "🚀 Crear y Publicar Campaña"
            """)
            
            if not advertising_top_manager_mode:
                gr.Markdown("""
                ⚠️ **Advertising Top Manager no está disponible.** 
                
                Verifica que las credenciales estén configuradas en `.env`:
                - `META_ACCESS_TOKEN`
                - `META_APP_ID`
                - `META_APP_SECRET`
                - `META_AD_ACCOUNT_ID`
                - `META_PAGE_ID`
                """)
            else:
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 📸 Sube tus Assets")
                        
                        image_files = gr.File(
                            label="Imágenes",
                            file_count="multiple",
                            file_types=["image"],
                            type="filepath"
                        )
                        
                        video_files = gr.File(
                            label="Videos",
                            file_count="multiple",
                            file_types=["video"],
                            type="filepath"
                        )
                        
                        gr.Markdown("""
                        **💡 Tip:** Puedes subir múltiples imágenes o videos. 
                        El sistema generará variaciones automáticamente.
                        """)
                    
                    with gr.Column(scale=1):
                        gr.Markdown("### ⚙️ Configuración de Campaña")
                        
                        campaign_name = gr.Textbox(
                            label="Nombre de la Campaña",
                            placeholder="Ej: Oferta Verano 2025",
                            value=""
                        )
                        
                        daily_budget = gr.Number(
                            label="Presupuesto Diario (USD)",
                            value=50.0,
                            minimum=1.0,
                            maximum=10000.0,
                            step=1.0
                        )
                        
                        objective = gr.Dropdown(
                            label="Objetivo de la Campaña",
                            choices=[
                                ("Conversiones", "CONVERSIONS"),
                                ("Tráfico", "TRAFFIC"),
                                ("Engagement", "ENGAGEMENT"),
                                ("Alcance", "AWARENESS"),
                                ("Generación de Leads", "LEAD_GENERATION"),
                                ("Ventas", "SALES")
                            ],
                            value="CONVERSIONS"
                        )
                        
                        platforms = gr.Dropdown(
                            label="Plataformas",
                            choices=[
                                ("Meta (Facebook/Instagram)", "meta"),
                                ("Google Ads", "google"),
                                ("Ambas", "both")
                            ],
                            value="both"
                        )
                        
                        auto_publish = gr.Checkbox(
                            label="🚀 Publicar Automáticamente (ACTIVE)",
                            value=True,
                            info="Si está marcado, los anuncios se publicarán automáticamente como ACTIVE. Si no, se crearán en PAUSED."
                        )
                        
                        landing_page_url = gr.Textbox(
                            label="URL de Página de Destino (Opcional)",
                            placeholder="https://tu-sitio.com/producto",
                            value=""
                        )
                        
                        target_audience = gr.Textbox(
                            label="Audiencia Objetivo (JSON Opcional)",
                            placeholder='{"age_min": 25, "age_max": 45, "genders": [1, 2], "interests": ["technology"]}',
                            value="",
                            lines=3
                        )
                
                # Botón de acción
                create_btn = gr.Button("🚀 Crear y Publicar Campaña", variant="primary", size="lg")
                
                # Output
                result_output = gr.Markdown(label="Resultado")
                result_json = gr.JSON(label="Datos de la Campaña", visible=False)
                
                # Handler
                create_btn.click(
                    fn=create_advertising_campaign_ui,
                    inputs=[campaign_name, daily_budget, objective, platforms, auto_publish, image_files, video_files, landing_page_url, target_audience],
                    outputs=[result_output, result_json]
                )
                
                # Información adicional
                with gr.Accordion("ℹ️ Información Adicional", open=False):
                    gr.Markdown("""
                    ### 🔑 Configuración Requerida
                    
                    Para usar Advertising Top Manager, necesitas configurar credenciales:
                    
                    **Meta Ads:**
                    - `META_ACCESS_TOKEN`
                    - `META_APP_ID`
                    - `META_APP_SECRET`
                    - `META_AD_ACCOUNT_ID`
                    - `META_PAGE_ID`
                    
                    **Google Ads:**
                    - `GOOGLE_ADS_CUSTOMER_ID`
                    - `GOOGLE_ADS_CONFIG_PATH` (ruta a google-ads.yaml)
                    
                    ### 📊 Después de Crear la Campaña
                    
                    - Los anuncios se procesarán y publicarán automáticamente
                    - Puedes ver las métricas en Meta Ads Manager y Google Ads
                    - El sistema generará múltiples variaciones de copy automáticamente
                    - Las mejores variaciones se seleccionarán automáticamente
                    
                    ### 🎯 Objetivos Disponibles
                    
                    - **CONVERSIONS:** Optimizar para conversiones
                    - **TRAFFIC:** Optimizar para tráfico al sitio
                    - **ENGAGEMENT:** Optimizar para engagement en redes sociales
                    - **AWARENESS:** Optimizar para alcance
                    - **LEAD_GENERATION:** Optimizar para generación de leads
                    - **SALES:** Optimizar para ventas
                    """)
"""

