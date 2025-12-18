"""
Knowledge Base Manager for RAG
Handles document loading, indexing, and retrieval
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

try:
    from langchain_community.document_loaders import TextLoader, PyPDFLoader, DirectoryLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS, Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain.retrievers import ContextualCompressionRetriever
    from langchain.retrievers.document_compressors import LLMChainExtractor
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from ..utils.logging import setup_logger

logger = setup_logger("customer_support.rag")


class KnowledgeBase:
    """Knowledge Base Manager with RAG capabilities"""
    
    def __init__(
        self,
        kb_path: str,
        vector_store_type: str = "faiss",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize Knowledge Base
        
        Args:
            kb_path: Path to knowledge base documents
            vector_store_type: "faiss" or "chroma"
            embedding_model: Hugging Face embedding model name
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain is required. Install with: pip install langchain langchain-community")
        
        self.kb_path = Path(kb_path)
        self.kb_path.mkdir(parents=True, exist_ok=True)
        self.vector_store_type = vector_store_type
        self.embedding_model = embedding_model
        
        # Initialize embeddings
        try:
            logger.info(f"🔄 Cargando modelo de embeddings: {embedding_model}")
            self.embeddings = HuggingFaceEmbeddings(
                model_name=embedding_model,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            logger.info("✅ Modelo de embeddings cargado")
        except Exception as e:
            logger.error(f"Error cargando embeddings: {e}")
            raise
        
        self.vector_store = None
        self.retriever = None
        
        # Create sample KB if empty
        self._create_sample_kb()
        
        # Load and index documents
        self._load_and_index()
    
    def _create_sample_kb(self):
        """Create sample knowledge base documents if KB is empty"""
        if list(self.kb_path.glob("*")):
            return  # KB already has files
        
        logger.info("📝 Creando base de conocimiento de ejemplo...")
        
        # Sample documents
        sample_docs = {
            "refund_policy.txt": """POLÍTICA DE REEMBOLSOS

Nuestra política de reembolsos es la siguiente:

1. Reembolsos dentro de 30 días: Los clientes pueden solicitar un reembolso completo dentro de 30 días de la compra si el producto no ha sido usado o está en su estado original.

2. Reembolsos parciales: Si el producto ha sido usado pero está defectuoso, ofrecemos reembolsos parciales del 50-80% dependiendo del estado.

3. Productos digitales: Los productos digitales no son elegibles para reembolso después de la descarga, excepto en casos de defectos técnicos.

4. Proceso de reembolso: Para solicitar un reembolso, el cliente debe contactar soporte con el número de orden. El reembolso se procesa en 5-7 días hábiles.

5. Métodos de pago: Los reembolsos se procesan al método de pago original usado en la compra.""",
            
            "shipping_faqs.txt": """PREGUNTAS FRECUENTES SOBRE ENVÍOS

1. ¿Cuánto tiempo tarda el envío?
   - Envío estándar: 5-7 días hábiles
   - Envío express: 2-3 días hábiles
   - Envío internacional: 10-15 días hábiles

2. ¿Cómo rastreo mi pedido?
   Puedes rastrear tu pedido usando el número de orden en nuestra página de rastreo o contactando soporte.

3. ¿Qué pasa si mi pedido está retrasado?
   Si tu pedido está retrasado más de 2 días hábiles, contacta soporte. Podemos ofrecer reembolsos parciales o envío express gratuito.

4. ¿Puedo cambiar la dirección de envío?
   Puedes cambiar la dirección antes de que el pedido sea enviado. Contacta soporte con tu número de orden.

5. ¿Qué pasa si mi paquete se pierde?
   Si tu paquete se pierde, te enviamos un reemplazo gratuito o un reembolso completo.""",
            
            "order_tracking.txt": """RASTREO DE PEDIDOS

Sistema de Rastreo:
- Todos los pedidos reciben un número de rastreo único
- El rastreo está disponible 24 horas después de la compra
- Puedes ver el estado en tiempo real en nuestra página

Estados del Pedido:
1. Procesando: Tu pedido está siendo preparado
2. Enviado: Tu pedido ha sido enviado y está en tránsito
3. En tránsito: Tu pedido está en camino a la dirección de entrega
4. Entregado: Tu pedido ha sido entregado
5. Retrasado: Tu pedido está retrasado (contacta soporte)

Tiempos Estimados:
- Procesamiento: 1-2 días hábiles
- Envío estándar: 5-7 días hábiles
- Envío express: 2-3 días hábiles""",
            
            "ticket_system.txt": """SISTEMA DE TICKETS DE SOPORTE

Cómo crear un ticket:
1. Contacta soporte a través del chat, email o teléfono
2. Proporciona detalles sobre tu problema
3. Recibirás un número de ticket único
4. Puedes rastrear el estado de tu ticket en línea

Tipos de Tickets:
- Técnico: Problemas con productos o servicios
- Facturación: Problemas con pagos o reembolsos
- Envío: Problemas con entregas
- General: Otras consultas

Tiempos de Respuesta:
- Urgente: 2-4 horas
- Alta: 4-8 horas
- Normal: 24 horas
- Baja: 48 horas

Escalación:
Si tu problema no se resuelve en 48 horas, el ticket se escala automáticamente a un supervisor.""",
            
            "product_info.txt": """INFORMACIÓN DE PRODUCTOS

Garantía:
- Todos los productos tienen garantía de 1 año
- La garantía cubre defectos de fabricación
- No cubre daños por uso normal o maltrato

Soporte Técnico:
- Disponible 24/7 por chat
- Email: support@empresa.com
- Teléfono: 1-800-SUPPORT

Devoluciones:
- Productos físicos: 30 días para devolución
- Productos digitales: No reembolsables después de descarga
- Productos usados: Reembolso parcial según estado"""
        }
        
        # Write sample documents
        for filename, content in sample_docs.items():
            file_path = self.kb_path / filename
            file_path.write_text(content, encoding='utf-8')
        
        logger.info(f"✅ {len(sample_docs)} documentos de ejemplo creados")
    
    def _load_and_index(self):
        """Load documents and create vector store"""
        logger.info("📚 Cargando y indexando documentos...")
        
        # Load documents
        documents = []
        loaders = []
        
        # Text files
        for txt_file in self.kb_path.glob("*.txt"):
            try:
                loader = TextLoader(str(txt_file), encoding='utf-8')
                loaders.append(loader)
            except Exception as e:
                logger.warning(f"Error cargando {txt_file}: {e}")
        
        # PDF files
        for pdf_file in self.kb_path.glob("*.pdf"):
            try:
                loader = PyPDFLoader(str(pdf_file))
                loaders.append(loader)
            except Exception as e:
                logger.warning(f"Error cargando {pdf_file}: {e}")
        
        # Load all documents
        for loader in loaders:
            try:
                docs = loader.load()
                documents.extend(docs)
            except Exception as e:
                logger.warning(f"Error procesando documentos: {e}")
        
        if not documents:
            logger.warning("⚠️ No se encontraron documentos para indexar")
            return
        
        logger.info(f"📄 {len(documents)} documentos cargados")
        
        # Split documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        splits = text_splitter.split_documents(documents)
        logger.info(f"📑 {len(splits)} chunks creados")
        
        # Create vector store
        try:
            if self.vector_store_type == "faiss":
                self.vector_store = FAISS.from_documents(splits, self.embeddings)
                logger.info("✅ Vector store FAISS creado")
            elif self.vector_store_type == "chroma":
                persist_directory = str(self.kb_path / "chroma_db")
                self.vector_store = Chroma.from_documents(
                    splits,
                    self.embeddings,
                    persist_directory=persist_directory
                )
                logger.info("✅ Vector store Chroma creado")
            else:
                raise ValueError(f"Tipo de vector store no soportado: {self.vector_store_type}")
        except Exception as e:
            logger.error(f"Error creando vector store: {e}")
            raise
        
        # Create retriever
        self.retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}  # Top 3 relevant chunks
        )
        
        logger.info("✅ Retriever configurado")
    
    def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Search knowledge base
        
        Args:
            query: Search query
            k: Number of results
            
        Returns:
            List of relevant documents with metadata
        """
        if not self.retriever:
            logger.warning("Retriever no inicializado")
            return []
        
        try:
            docs = self.retriever.get_relevant_documents(query)
            
            results = []
            for doc in docs:
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": getattr(doc, 'score', None)
                })
            
            logger.info(f"🔍 Búsqueda completada: {len(results)} resultados para '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            return []
    
    def add_document(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Add new document to knowledge base
        
        Args:
            content: Document content
            metadata: Optional metadata
        """
        if not self.vector_store:
            logger.warning("Vector store no inicializado")
            return
        
        try:
            from langchain.schema import Document
            doc = Document(page_content=content, metadata=metadata or {})
            self.vector_store.add_documents([doc])
            logger.info("✅ Documento agregado a la base de conocimiento")
        except Exception as e:
            logger.error(f"Error agregando documento: {e}")

