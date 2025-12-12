"""
Base de datos PostgreSQL para Ads Optimization Engine
Reemplaza archivos JSON con base de datos real
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

try:
    from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, JSON, Text, ForeignKey
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, Session, relationship
    from sqlalchemy.pool import QueuePool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    print("⚠️ SQLAlchemy no disponible. Instala con: pip install sqlalchemy psycopg2-binary")

if SQLALCHEMY_AVAILABLE:
    Base = declarative_base()
else:
    Base = None


if SQLALCHEMY_AVAILABLE:
    class CreativeAssetDB(Base):
        """Tabla de assets creativos"""
        __tablename__ = "creative_assets"
        
        asset_id = Column(String, primary_key=True)
        tenant_id = Column(String, nullable=False, index=True)
        asset_type = Column(String, nullable=False)  # text, image, video
        file_path = Column(String)
        file_size = Column(Integer)
        mime_type = Column(String)
        metadata = Column(JSON)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    class AdVariationDB(Base):
        """Tabla de variaciones de anuncios"""
        __tablename__ = "ad_variations"
        
        variation_id = Column(String, primary_key=True)
        tenant_id = Column(String, nullable=False, index=True)
        original_asset_id = Column(String, ForeignKey("creative_assets.asset_id"))
        headline = Column(Text)
        description = Column(Text)
        image_path = Column(String)
        video_path = Column(String)
        predicted_ctr = Column(Float)
        predicted_cpc = Column(Float)
        predicted_conversion_prob = Column(Float)
        quality_score = Column(Float)
        metadata = Column(JSON)
        created_at = Column(DateTime, default=datetime.utcnow)
        
        # Relación
        asset = relationship("CreativeAssetDB", backref="variations")
    
    class CampaignDB(Base):
        """Tabla de campañas"""
        __tablename__ = "campaigns"
        
        campaign_id = Column(String, primary_key=True)
        tenant_id = Column(String, nullable=False, index=True)
        name = Column(String, nullable=False)
        platform = Column(String, nullable=False)  # meta, google, tiktok
        objective = Column(String, nullable=False)  # awareness, traffic, etc.
        budget = Column(Float, nullable=False)
        daily_budget = Column(Float)
        start_date = Column(DateTime)
        end_date = Column(DateTime)
        status = Column(String, default="draft")  # draft, active, paused, completed
        target_audience = Column(JSON)
        platform_campaign_id = Column(String)  # ID en la plataforma externa
        metadata = Column(JSON)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        launched_at = Column(DateTime)
    
    class CampaignVariationDB(Base):
        """Tabla de relación campaña-variaciones"""
        __tablename__ = "campaign_variations"
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        campaign_id = Column(String, ForeignKey("campaigns.campaign_id"), nullable=False)
        variation_id = Column(String, ForeignKey("ad_variations.variation_id"), nullable=False)
        created_at = Column(DateTime, default=datetime.utcnow)
    
    class PerformanceMetricsDB(Base):
        """Tabla de métricas de performance"""
        __tablename__ = "performance_metrics"
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        tenant_id = Column(String, nullable=False, index=True)
        campaign_id = Column(String, ForeignKey("campaigns.campaign_id"), nullable=False, index=True)
        variation_id = Column(String, ForeignKey("ad_variations.variation_id"))
        impressions = Column(Integer, default=0)
        clicks = Column(Integer, default=0)
        conversions = Column(Integer, default=0)
        spend = Column(Float, default=0.0)
        ctr = Column(Float, default=0.0)
        cpc = Column(Float, default=0.0)
        cpm = Column(Float, default=0.0)
        cpa = Column(Float, default=0.0)
        roas = Column(Float, default=0.0)
        conversion_rate = Column(Float, default=0.0)
        timestamp = Column(DateTime, default=datetime.utcnow, index=True)
        metadata = Column(JSON)
    
    class OptimizationHistoryDB(Base):
        """Tabla de historial de optimizaciones"""
        __tablename__ = "optimization_history"
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        tenant_id = Column(String, nullable=False, index=True)
        campaign_id = Column(String, ForeignKey("campaigns.campaign_id"), nullable=False, index=True)
        optimization_type = Column(String)  # rl_bidding, scaling, etc.
        old_value = Column(JSON)
        new_value = Column(JSON)
        reward = Column(Float)
        timestamp = Column(DateTime, default=datetime.utcnow, index=True)
        metadata = Column(JSON)


class DatabaseManager:
    """Gestor de base de datos PostgreSQL"""
    
    def __init__(self, config: Any):
        self.config = config
        
        if not SQLALCHEMY_AVAILABLE:
            self.engine = None
            self.Session = None
            self.use_fallback = True
            return
        
        # Obtener connection string
        db_url = os.getenv(
            "ADS_DATABASE_URL",
            f"sqlite:///{Path(config.memory_dir if config.memory_dir else 'data') / 'ads_optimization.db'}"
        )
        
        # Si no hay PostgreSQL, usar SQLite como fallback
        if "postgresql" not in db_url and "postgres" not in db_url:
            db_url = db_url.replace("sqlite:///", "sqlite:///")
            self.use_fallback = True
        else:
            self.use_fallback = False
        
        try:
            self.engine = create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,  # Verificar conexiones antes de usar
                echo=False
            )
            self.Session = sessionmaker(bind=self.engine)
            
            # Crear tablas si no existen
            Base.metadata.create_all(self.engine)
            
            print(f"✅ Base de datos conectada: {db_url.split('@')[-1] if '@' in db_url else db_url}")
        except Exception as e:
            print(f"⚠️ Error conectando a base de datos: {e}")
            print("⚠️ Usando fallback a archivos JSON")
            self.engine = None
            self.Session = None
            self.use_fallback = True
    
    def get_session(self) -> Optional[Session]:
        """Obtiene una sesión de base de datos"""
        if self.Session is None:
            return None
        return self.Session()
    
    def create_asset(
        self,
        asset_id: str,
        tenant_id: str,
        asset_type: str,
        file_path: Optional[str] = None,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Crea un asset en la base de datos"""
        if self.use_fallback or not SQLALCHEMY_AVAILABLE:
            return False
        
        try:
            session = self.get_session()
            if session is None:
                return False
            
            asset = CreativeAssetDB(
                asset_id=asset_id,
                tenant_id=tenant_id,
                asset_type=asset_type,
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type,
                metadata=metadata or {}
            )
            session.add(asset)
            session.commit()
            session.close()
            return True
        except Exception as e:
            print(f"Error creando asset en DB: {e}")
            return False
    
    def get_asset(self, asset_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un asset de la base de datos"""
        if self.use_fallback or not SQLALCHEMY_AVAILABLE:
            return None
        
        try:
            session = self.get_session()
            if session is None:
                return None
            
            asset = session.query(CreativeAssetDB).filter(
                CreativeAssetDB.asset_id == asset_id,
                CreativeAssetDB.tenant_id == tenant_id
            ).first()
            
            if asset:
                result = {
                    "asset_id": asset.asset_id,
                    "asset_type": asset.asset_type,
                    "file_path": asset.file_path,
                    "file_size": asset.file_size,
                    "mime_type": asset.mime_type,
                    "metadata": asset.metadata or {},
                    "created_at": asset.created_at.isoformat() if asset.created_at else None
                }
                session.close()
                return result
            
            session.close()
            return None
        except Exception as e:
            print(f"Error obteniendo asset de DB: {e}")
            return None
    
    def create_campaign(
        self,
        campaign_id: str,
        tenant_id: str,
        name: str,
        platform: str,
        objective: str,
        budget: float,
        daily_budget: Optional[float] = None,
        target_audience: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Crea una campaña en la base de datos"""
        if self.use_fallback or not SQLALCHEMY_AVAILABLE:
            return False
        
        try:
            session = self.get_session()
            if session is None:
                return False
            
            campaign = CampaignDB(
                campaign_id=campaign_id,
                tenant_id=tenant_id,
                name=name,
                platform=platform,
                objective=objective,
                budget=budget,
                daily_budget=daily_budget,
                target_audience=target_audience or {},
                metadata=metadata or {},
                status="draft"
            )
            session.add(campaign)
            session.commit()
            session.close()
            return True
        except Exception as e:
            print(f"Error creando campaña en DB: {e}")
            return False
    
    def save_performance_metrics(
        self,
        tenant_id: str,
        campaign_id: str,
        variation_id: Optional[str],
        impressions: int,
        clicks: int,
        conversions: int,
        spend: float,
        ctr: float,
        cpc: float,
        cpm: float,
        cpa: float,
        roas: float,
        conversion_rate: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Guarda métricas de performance"""
        if self.use_fallback or not SQLALCHEMY_AVAILABLE:
            return False
        
        try:
            session = self.get_session()
            if session is None:
                return False
            
            metrics = PerformanceMetricsDB(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                variation_id=variation_id,
                impressions=impressions,
                clicks=clicks,
                conversions=conversions,
                spend=spend,
                ctr=ctr,
                cpc=cpc,
                cpm=cpm,
                cpa=cpa,
                roas=roas,
                conversion_rate=conversion_rate,
                metadata=metadata or {}
            )
            session.add(metrics)
            session.commit()
            session.close()
            return True
        except Exception as e:
            print(f"Error guardando métricas en DB: {e}")
            return False

