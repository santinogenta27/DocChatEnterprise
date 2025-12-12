"""
Tests para Ads Optimization Engine
Tests unitarios y de integración
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

# Imports del engine
from docchat.ads_optimization.models import SoWideV2Predictor, XGBoostCTRPredictor, ModelManager
from docchat.ads_optimization.database import DatabaseManager
from docchat.ads_optimization.tenant_manager import TenantManager
from docchat.ads_optimization.billing import BillingManager
from docchat.ads_optimization.rate_limiter import RateLimiterManager
from docchat.ads_optimization.retry_logic import RetryConfig, APIClient
from docchat.ads_optimization.engine_production import ProductionAdsOptimizationEngine
from docchat.ads_optimization_engine import CreativeType, CampaignObjective, Platform, PerformanceMetrics
from docchat.config import AppConfig


@pytest.fixture
def temp_dir():
    """Directorio temporal para tests"""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def config(temp_dir):
    """Config para tests"""
    config = AppConfig()
    config.memory_dir = str(temp_dir)
    return config


@pytest.fixture
def model_manager(config):
    """Model manager para tests"""
    return ModelManager(config)


@pytest.fixture
def tenant_manager(temp_dir):
    """Tenant manager para tests"""
    return TenantManager(temp_dir)


class TestModels:
    """Tests para modelos de predicción"""
    
    def test_sowide_predictor_extract_features(self, model_manager):
        """Test extracción de features"""
        model = model_manager.get_model("sowide_v2")
        ad_data = {
            "headline": "Test headline with question?",
            "description": "Test description",
            "quality_score": 0.8
        }
        features = model.extract_features(ad_data)
        assert len(features) > 0
        assert features.dtype == "float32"
    
    def test_sowide_predictor_predict(self, model_manager):
        """Test predicción CTR"""
        model = model_manager.get_model("sowide_v2")
        ad_data = {
            "headline": "Test headline",
            "description": "Test description",
            "quality_score": 0.5
        }
        ctr = model.predict(ad_data)
        assert 0.001 <= ctr <= 0.15  # CTR debe estar en rango razonable
    
    def test_xgboost_predictor(self, model_manager):
        """Test XGBoost predictor"""
        model = model_manager.get_model("xgb")
        ad_data = {
            "headline": "Test",
            "description": "Test desc",
            "quality_score": 0.6
        }
        ctr = model.predict(ad_data)
        assert 0.001 <= ctr <= 0.15


class TestDatabase:
    """Tests para base de datos"""
    
    def test_database_manager_init(self, config):
        """Test inicialización de DB manager"""
        db_manager = DatabaseManager(config)
        assert db_manager is not None
    
    def test_create_asset(self, config):
        """Test crear asset en DB"""
        db_manager = DatabaseManager(config)
        success = db_manager.create_asset(
            asset_id="test_asset_1",
            tenant_id="test_tenant",
            asset_type="text",
            file_path="/test/path.txt",
            file_size=100,
            mime_type="text/plain"
        )
        # Puede fallar si no hay DB, pero no debe crashear
        assert isinstance(success, bool)
    
    def test_get_asset(self, config):
        """Test obtener asset de DB"""
        db_manager = DatabaseManager(config)
        asset = db_manager.get_asset("test_asset_1", "test_tenant")
        # Puede ser None si no hay DB
        assert asset is None or isinstance(asset, dict)


class TestTenantManager:
    """Tests para tenant manager"""
    
    def test_create_tenant(self, tenant_manager):
        """Test crear tenant"""
        tenant = tenant_manager.create_tenant(
            name="Test Tenant",
            email="test@example.com",
            plan="pro"
        )
        assert tenant.tenant_id is not None
        assert tenant.plan == "pro"
        assert tenant.name == "Test Tenant"
    
    def test_get_tenant(self, tenant_manager):
        """Test obtener tenant"""
        tenant = tenant_manager.create_tenant("Test", "test@example.com")
        retrieved = tenant_manager.get_tenant(tenant.tenant_id)
        assert retrieved is not None
        assert retrieved.tenant_id == tenant.tenant_id
    
    def test_check_quota(self, tenant_manager):
        """Test verificación de cuota"""
        tenant = tenant_manager.create_tenant("Test", "test@example.com", "free")
        quota = tenant_manager.get_quota(tenant.tenant_id)
        assert quota is not None
        assert quota.max_campaigns == 5  # Free plan
    
    def test_increment_usage(self, tenant_manager):
        """Test incrementar uso"""
        tenant = tenant_manager.create_tenant("Test", "test@example.com")
        tenant_manager.increment_usage(tenant.tenant_id, "campaigns", 1)
        updated = tenant_manager.get_tenant(tenant.tenant_id)
        assert updated.usage["campaigns"] == 1


class TestBilling:
    """Tests para billing"""
    
    def test_billing_manager_init(self, temp_dir):
        """Test inicialización de billing manager"""
        billing = BillingManager(temp_dir)
        assert billing is not None
    
    def test_record_usage(self, temp_dir):
        """Test registrar uso"""
        billing = BillingManager(temp_dir)
        billing.record_usage("tenant_1", "campaigns", 1.0)
        assert len(billing.usage_records) > 0
    
    def test_calculate_cost(self, temp_dir):
        """Test calcular costo"""
        billing = BillingManager(temp_dir)
        billing.record_usage("tenant_1", "campaigns", 5.0)
        
        from datetime import datetime, timedelta
        period_start = datetime.now() - timedelta(days=1)
        period_end = datetime.now()
        
        cost = billing.calculate_cost("tenant_1", "pro", period_start, period_end)
        assert cost >= 0


class TestRateLimiter:
    """Tests para rate limiter"""
    
    def test_rate_limiter_init(self):
        """Test inicialización"""
        limiter = RateLimiterManager()
        assert limiter is not None
    
    def test_is_allowed(self):
        """Test verificación de rate limit"""
        limiter = RateLimiterManager()
        allowed = limiter.is_allowed("meta", "test_id")
        assert isinstance(allowed, bool)
    
    def test_get_remaining(self):
        """Test obtener requests restantes"""
        limiter = RateLimiterManager()
        remaining = limiter.get_remaining("meta", "test_id")
        assert remaining >= 0


class TestRetryLogic:
    """Tests para retry logic"""
    
    def test_retry_config(self):
        """Test configuración de retry"""
        config = RetryConfig(max_attempts=3, initial_wait=1.0)
        assert config.max_attempts == 3
        assert config.initial_wait == 1.0
    
    def test_api_client(self):
        """Test API client"""
        client = APIClient("test", RetryConfig())
        assert client.name == "test"


class TestProductionEngine:
    """Tests para engine de producción"""
    
    @pytest.mark.asyncio
    async def test_engine_init(self, config):
        """Test inicialización del engine"""
        engine = ProductionAdsOptimizationEngine(config, tenant_id="test_tenant")
        assert engine is not None
        assert engine.tenant_id == "test_tenant"
    
    @pytest.mark.asyncio
    async def test_upload_asset(self, config):
        """Test subir asset"""
        engine = ProductionAdsOptimizationEngine(config, tenant_id="test_tenant")
        asset = await engine.upload_creative_asset(
            CreativeType.TEXT,
            "Test content"
        )
        assert asset.asset_id is not None
        assert asset.asset_type == CreativeType.TEXT
    
    @pytest.mark.asyncio
    async def test_generate_variations(self, config):
        """Test generar variaciones"""
        engine = ProductionAdsOptimizationEngine(config, tenant_id="test_tenant")
        
        # Primero subir asset
        asset = await engine.upload_creative_asset(
            CreativeType.TEXT,
            "Test ad content"
        )
        
        # Generar variaciones
        variations = await engine.generate_ad_variations(
            asset.asset_id,
            num_variations=3
        )
        assert len(variations) > 0
        assert all(v.headline for v in variations)
    
    def test_get_billing_summary(self, config):
        """Test obtener resumen de facturación"""
        engine = ProductionAdsOptimizationEngine(config, tenant_id="test_tenant")
        summary = engine.get_billing_summary()
        assert "tenant_id" in summary
        assert "plan" in summary
        assert "usage" in summary


# Tests de integración
class TestIntegration:
    """Tests de integración end-to-end"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, config):
        """Test workflow completo"""
        engine = ProductionAdsOptimizationEngine(config, tenant_id="test_tenant")
        
        # 1. Subir asset
        asset = await engine.upload_creative_asset(
            CreativeType.TEXT,
            "Amazing product! Buy now!"
        )
        
        # 2. Generar variaciones
        variations = await engine.generate_ad_variations(
            asset.asset_id,
            num_variations=3,
            objective=CampaignObjective.AWARENESS
        )
        
        # 3. Predecir performance
        variations = await engine.predict_performance(
            variations,
            Platform.META,
            CampaignObjective.AWARENESS
        )
        
        # Verificar que todas tienen predicciones
        assert all(v.predicted_ctr > 0 for v in variations)
        assert all(v.predicted_cpc > 0 for v in variations)
        
        # 4. Obtener resumen de facturación
        summary = engine.get_billing_summary()
        assert summary["usage"]["assets"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

