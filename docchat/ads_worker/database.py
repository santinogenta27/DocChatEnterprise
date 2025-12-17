"""
Database Manager for ADS WORKER
SQLite/PostgreSQL database for campaigns, assets, and metrics
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import os
import json

try:
    from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, JSON, Text, ForeignKey, Index
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, Session, relationship
    from sqlalchemy.pool import QueuePool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    print("⚠️ SQLAlchemy no disponible. Instala con: pip install sqlalchemy")

if SQLALCHEMY_AVAILABLE:
    Base = declarative_base()
else:
    Base = None


if SQLALCHEMY_AVAILABLE:
    class AssetDB(Base):
        """Tabla de assets subidos por usuarios"""
        __tablename__ = "assets"
        
        asset_id = Column(String, primary_key=True)
        user_id = Column(String, index=True)
        asset_type = Column(String, nullable=False)  # image, video, text
        file_path = Column(String)
        file_url = Column(String)
        text_content = Column(Text)
        file_size = Column(Integer)
        mime_type = Column(String)
        metadata = Column(JSON)
        analysis_result = Column(JSON)  # Resultado del análisis
        created_at = Column(DateTime, default=datetime.utcnow, index=True)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    class CreativeDB(Base):
        """Tabla de creativos generados"""
        __tablename__ = "creatives"
        
        creative_id = Column(String, primary_key=True)
        asset_id = Column(String, ForeignKey("assets.asset_id"), nullable=False, index=True)
        creative_type = Column(String, nullable=False)  # copy, visual, video
        headline = Column(String)
        description = Column(Text)
        cta = Column(String)
        visual_url = Column(String)
        video_url = Column(String)
        format = Column(String)
        generation_params = Column(JSON)
        performance_score = Column(Float)
        created_at = Column(DateTime, default=datetime.utcnow)
    
    class CampaignDB(Base):
        """Tabla de campañas"""
        __tablename__ = "campaigns"
        
        campaign_id = Column(String, primary_key=True)
        user_id = Column(String, index=True)
        name = Column(String, nullable=False)
        objective = Column(String, nullable=False)
        budget_daily = Column(Float, nullable=False)
        budget_total = Column(Float)
        budget_spent = Column(Float, default=0.0)
        platforms = Column(String)  # meta, google, both
        status = Column(String, default="draft")  # draft, active, paused, completed
        optimization_goal = Column(String, default="conversions")
        auto_optimize = Column(Boolean, default=True)
        start_date = Column(DateTime)
        end_date = Column(DateTime)
        metadata = Column(JSON)
        platform_campaign_ids = Column(JSON)  # {platform: campaign_id}
        created_at = Column(DateTime, default=datetime.utcnow, index=True)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        __table_args__ = (
            Index('idx_campaign_user_status', 'user_id', 'status'),
        )
    
    class AdDB(Base):
        """Tabla de anuncios creados"""
        __tablename__ = "ads"
        
        ad_id = Column(String, primary_key=True)
        campaign_id = Column(String, ForeignKey("campaigns.campaign_id"), nullable=False, index=True)
        creative_id = Column(String, ForeignKey("creatives.creative_id"), nullable=False)
        platform = Column(String, nullable=False)  # meta, google
        platform_ad_id = Column(String)  # ID en la plataforma externa
        status = Column(String, default="active")  # active, paused, archived
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        
        __table_args__ = (
            Index('idx_ad_campaign_platform', 'campaign_id', 'platform'),
        )
    
    class PerformanceMetricsDB(Base):
        """Tabla de métricas de performance"""
        __tablename__ = "performance_metrics"
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        ad_id = Column(String, ForeignKey("ads.ad_id"), nullable=False, index=True)
        campaign_id = Column(String, ForeignKey("campaigns.campaign_id"), nullable=False, index=True)
        platform = Column(String, nullable=False)
        impressions = Column(Integer, default=0)
        clicks = Column(Integer, default=0)
        conversions = Column(Integer, default=0)
        spend = Column(Float, default=0.0)
        ctr = Column(Float, default=0.0)
        cpc = Column(Float, default=0.0)
        cpa = Column(Float, default=0.0)
        roas = Column(Float, default=0.0)
        timestamp = Column(DateTime, default=datetime.utcnow, index=True)
        metrics_metadata = Column(JSON)
        
        __table_args__ = (
            Index('idx_metrics_ad_timestamp', 'ad_id', 'timestamp'),
            Index('idx_metrics_campaign_timestamp', 'campaign_id', 'timestamp'),
        )
    
    class OptimizationHistoryDB(Base):
        """Tabla de historial de optimizaciones"""
        __tablename__ = "optimization_history"
        
        id = Column(Integer, primary_key=True, autoincrement=True)
        optimization_id = Column(String, index=True)
        campaign_id = Column(String, ForeignKey("campaigns.campaign_id"), nullable=False, index=True)
        ads_paused = Column(JSON)  # Lista de ad_ids pausados
        ads_scaled = Column(JSON)  # Lista de ad_ids escalados
        budget_reallocated = Column(JSON)  # {ad_id: new_budget}
        performance_improvement = Column(JSON)
        recommendations = Column(JSON)
        timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class DatabaseManager:
    """Gestor de base de datos para ADS WORKER"""
    
    def __init__(self, db_url: Optional[str] = None, memory_dir: Optional[str] = None):
        """
        Initialize database manager
        
        Args:
            db_url: Database URL (postgresql://... or sqlite:///...)
            memory_dir: Directory for SQLite if using local storage
        """
        if not SQLALCHEMY_AVAILABLE:
            self.engine = None
            self.Session = None
            self.use_fallback = True
            print("⚠️ SQLAlchemy no disponible, usando almacenamiento en memoria")
            return
        
        # Determine database URL
        if not db_url:
            if memory_dir:
                db_path = Path(memory_dir) / "ads_worker.db"
            else:
                db_path = Path("./data") / "ads_worker.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            db_url = f"sqlite:///{db_path}"
        
        self.use_fallback = "sqlite" in db_url or "postgresql" not in db_url
        
        try:
            self.engine = create_engine(
                db_url,
                poolclass=QueuePool if "postgresql" in db_url else None,
                pool_size=5 if "postgresql" in db_url else None,
                max_overflow=10 if "postgresql" in db_url else None,
                pool_pre_ping=True,
                echo=False
            )
            self.Session = sessionmaker(bind=self.engine)
            
            # Create tables
            Base.metadata.create_all(self.engine)
            
            print(f"✅ Base de datos ADS WORKER conectada: {db_url}")
        except Exception as e:
            print(f"⚠️ Error conectando a base de datos: {e}")
            self.engine = None
            self.Session = None
            self.use_fallback = True
    
    def get_session(self) -> Optional[Session]:
        """Get database session"""
        if not self.Session:
            return None
        return self.Session()
    
    def save_asset(
        self,
        asset_id: str,
        user_id: str,
        asset_type: str,
        file_path: Optional[str] = None,
        file_url: Optional[str] = None,
        text_content: Optional[str] = None,
        analysis_result: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save asset to database"""
        if self.use_fallback or not SQLALCHEMY_AVAILABLE:
            return False
        
        try:
            session = self.get_session()
            if not session:
                return False
            
            asset = AssetDB(
                asset_id=asset_id,
                user_id=user_id,
                asset_type=asset_type,
                file_path=file_path,
                file_url=file_url,
                text_content=text_content,
                file_size=os.path.getsize(file_path) if file_path and os.path.exists(file_path) else None,
                mime_type=self._get_mime_type(file_path) if file_path else None,
                analysis_result=analysis_result,
                metadata=metadata or {}
            )
            
            session.add(asset)
            session.commit()
            session.close()
            return True
        except Exception as e:
            print(f"⚠️ Error guardando asset: {e}")
            return False
    
    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Get asset from database"""
        if self.use_fallback or not SQLALCHEMY_AVAILABLE:
            return None
        
        try:
            session = self.get_session()
            if not session:
                return None
            
            asset = session.query(AssetDB).filter(AssetDB.asset_id == asset_id).first()
            if asset:
                result = {
                    "asset_id": asset.asset_id,
                    "user_id": asset.user_id,
                    "asset_type": asset.asset_type,
                    "file_path": asset.file_path,
                    "file_url": asset.file_url,
                    "text_content": asset.text_content,
                    "analysis_result": asset.analysis_result,
                    "metadata": asset.metadata or {},
                    "created_at": asset.created_at.isoformat() if asset.created_at else None
                }
                session.close()
                return result
            
            session.close()
            return None
        except Exception as e:
            print(f"⚠️ Error obteniendo asset: {e}")
            return None
    
    def save_campaign(
        self,
        campaign_id: str,
        user_id: str,
        name: str,
        objective: str,
        budget_daily: float,
        platforms: str,
        platform_campaign_ids: Dict[str, str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save campaign to database"""
        if self.use_fallback or not SQLALCHEMY_AVAILABLE:
            return False
        
        try:
            session = self.get_session()
            if not session:
                return False
            
            campaign = CampaignDB(
                campaign_id=campaign_id,
                user_id=user_id,
                name=name,
                objective=objective,
                budget_daily=budget_daily,
                platforms=platforms,
                status="active",
                platform_campaign_ids=platform_campaign_ids,
                metadata=metadata or {}
            )
            
            session.add(campaign)
            session.commit()
            session.close()
            return True
        except Exception as e:
            print(f"⚠️ Error guardando campaña: {e}")
            return False
    
    def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get campaign from database"""
        if self.use_fallback or not SQLALCHEMY_AVAILABLE:
            return None
        
        try:
            session = self.get_session()
            if not session:
                return None
            
            campaign = session.query(CampaignDB).filter(CampaignDB.campaign_id == campaign_id).first()
            if campaign:
                result = {
                    "campaign_id": campaign.campaign_id,
                    "user_id": campaign.user_id,
                    "name": campaign.name,
                    "objective": campaign.objective,
                    "budget_daily": campaign.budget_daily,
                    "budget_spent": campaign.budget_spent or 0.0,
                    "platforms": campaign.platforms,
                    "status": campaign.status,
                    "platform_campaign_ids": campaign.platform_campaign_ids or {},
                    "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
                    "updated_at": campaign.updated_at.isoformat() if campaign.updated_at else None
                }
                session.close()
                return result
            
            session.close()
            return None
        except Exception as e:
            print(f"⚠️ Error obteniendo campaña: {e}")
            return None
    
    def save_metrics(
        self,
        ad_id: str,
        campaign_id: str,
        platform: str,
        metrics: Dict[str, Any]
    ) -> bool:
        """Save performance metrics"""
        if self.use_fallback or not SQLALCHEMY_AVAILABLE:
            return False
        
        try:
            session = self.get_session()
            if not session:
                return False
            
            perf_metrics = PerformanceMetricsDB(
                ad_id=ad_id,
                campaign_id=campaign_id,
                platform=platform,
                impressions=metrics.get("impressions", 0),
                clicks=metrics.get("clicks", 0),
                conversions=metrics.get("conversions", 0),
                spend=metrics.get("spend", 0.0),
                ctr=metrics.get("ctr", 0.0),
                cpc=metrics.get("cpc", 0.0),
                cpa=metrics.get("cpa", 0.0),
                roas=metrics.get("roas", 0.0),
                metrics_metadata=metrics.get("metadata", {})
            )
            
            session.add(perf_metrics)
            session.commit()
            session.close()
            return True
        except Exception as e:
            print(f"⚠️ Error guardando métricas: {e}")
            return False
    
    def get_campaign_metrics(
        self,
        campaign_id: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get campaign metrics for last N hours"""
        if self.use_fallback or not SQLALCHEMY_AVAILABLE:
            return []
        
        try:
            session = self.get_session()
            if not session:
                return []
            
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            metrics = session.query(PerformanceMetricsDB).filter(
                PerformanceMetricsDB.campaign_id == campaign_id,
                PerformanceMetricsDB.timestamp >= cutoff_time
            ).all()
            
            results = []
            for m in metrics:
                results.append({
                    "ad_id": m.ad_id,
                    "platform": m.platform,
                    "impressions": m.impressions,
                    "clicks": m.clicks,
                    "conversions": m.conversions,
                    "spend": m.spend,
                    "ctr": m.ctr,
                    "cpc": m.cpc,
                    "cpa": m.cpa,
                    "roas": m.roas,
                    "timestamp": m.timestamp.isoformat() if m.timestamp else None
                })
            
            session.close()
            return results
        except Exception as e:
            print(f"⚠️ Error obteniendo métricas: {e}")
            return []
    
    def _get_mime_type(self, file_path: str) -> Optional[str]:
        """Get MIME type from file path"""
        ext = Path(file_path).suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo'
        }
        return mime_types.get(ext, 'application/octet-stream')
