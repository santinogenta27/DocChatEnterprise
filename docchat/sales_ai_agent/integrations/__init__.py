"""Integraciones para Sales AI Agent."""

from .shopify_integration import ShopifyIntegration, ShopifyProduct
from .woocommerce_integration import WooCommerceIntegration, WooCommerceProduct
from .url_crawler import URLCrawler, CrawledPage

# Integraciones OPCIONALES (configurables por separado)
try:
    from .meta_api_integration import MetaAPIIntegration, MetaPost, MetaAdCampaign
    META_API_AVAILABLE = True
except ImportError:
    META_API_AVAILABLE = False
    MetaAPIIntegration = None
    MetaPost = None
    MetaAdCampaign = None

try:
    from .website_learner import WebsiteLearner, WebsitePage
    WEBSITE_LEARNER_AVAILABLE = True
except ImportError:
    WEBSITE_LEARNER_AVAILABLE = False
    WebsiteLearner = None
    WebsitePage = None

try:
    from .whatsapp_integration import WhatsAppIntegration, WhatsAppMessage
    WHATSAPP_AVAILABLE = True
except ImportError:
    WHATSAPP_AVAILABLE = False
    WhatsAppIntegration = None
    WhatsAppMessage = None

__all__ = [
    "ShopifyIntegration",
    "ShopifyProduct",
    "WooCommerceIntegration",
    "WooCommerceProduct",
    "URLCrawler",
    "CrawledPage",
]

# Agregar integraciones opcionales si están disponibles
if META_API_AVAILABLE:
    __all__.extend(["MetaAPIIntegration", "MetaPost", "MetaAdCampaign"])

if WEBSITE_LEARNER_AVAILABLE:
    __all__.extend(["WebsiteLearner", "WebsitePage"])

if WHATSAPP_AVAILABLE:
    __all__.extend(["WhatsAppIntegration", "WhatsAppMessage"])

