"""
Adaptador de configuración: Convierte AppConfig a configuración compatible con BettaFish
"""

import os
from typing import Optional, Literal
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from ..config import AppConfig


def create_bettafish_config(app_config: AppConfig) -> BaseSettings:
    """Crea un objeto Settings compatible con BettaFish desde AppConfig"""
    
    output_dir = str(app_config.memory_dir / "vision_alpha_reports")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    class BettaFishSettings(BaseSettings):
        """Configuración compatible con BettaFish engines"""
        
        # LLM配置
        QUERY_ENGINE_API_KEY: Optional[str] = Field(
            default=app_config.openai_api_key,
            description="Query Engine LLM API密钥"
        )
        QUERY_ENGINE_BASE_URL: Optional[str] = Field(
            default=os.getenv("QUERY_ENGINE_BASE_URL", "https://api.openai.com/v1"),
            description="Query Engine LLM BaseUrl"
        )
        QUERY_ENGINE_MODEL_NAME: str = Field(
            default=os.getenv("QUERY_ENGINE_MODEL_NAME", app_config.openai_model),
            description="Query Engine LLM模型名称"
        )
        
        MEDIA_ENGINE_API_KEY: Optional[str] = Field(
            default=app_config.openai_api_key,
            description="Media Engine LLM API密钥"
        )
        MEDIA_ENGINE_BASE_URL: Optional[str] = Field(
            default=os.getenv("MEDIA_ENGINE_BASE_URL", "https://api.openai.com/v1"),
            description="Media Engine LLM BaseUrl"
        )
        MEDIA_ENGINE_MODEL_NAME: str = Field(
            default=os.getenv("MEDIA_ENGINE_MODEL_NAME", app_config.openai_model),
            description="Media Engine LLM模型名称"
        )
        
        INSIGHT_ENGINE_API_KEY: Optional[str] = Field(
            default=app_config.openai_api_key,
            description="Insight Engine LLM API密钥"
        )
        INSIGHT_ENGINE_BASE_URL: Optional[str] = Field(
            default=os.getenv("INSIGHT_ENGINE_BASE_URL", "https://api.openai.com/v1"),
            description="Insight Engine LLM BaseUrl"
        )
        INSIGHT_ENGINE_MODEL_NAME: str = Field(
            default=os.getenv("INSIGHT_ENGINE_MODEL_NAME", app_config.openai_model),
            description="Insight Engine LLM模型名称"
        )
        
        REPORT_ENGINE_API_KEY: Optional[str] = Field(
            default=app_config.openai_api_key,
            description="Report Engine LLM API密钥"
        )
        REPORT_ENGINE_BASE_URL: Optional[str] = Field(
            default=os.getenv("REPORT_ENGINE_BASE_URL", "https://api.openai.com/v1"),
            description="Report Engine LLM BaseUrl"
        )
        REPORT_ENGINE_MODEL_NAME: str = Field(
            default=os.getenv("REPORT_ENGINE_MODEL_NAME", app_config.openai_model),
            description="Report Engine LLM模型名称"
        )
        
        FORUM_HOST_API_KEY: Optional[str] = Field(
            default=app_config.openai_api_key,
            description="Forum Host LLM API密钥"
        )
        FORUM_HOST_BASE_URL: Optional[str] = Field(
            default=os.getenv("FORUM_HOST_BASE_URL", "https://api.openai.com/v1"),
            description="Forum Host LLM BaseUrl"
        )
        FORUM_HOST_MODEL_NAME: Optional[str] = Field(
            default=os.getenv("FORUM_HOST_MODEL_NAME", app_config.openai_model),
            description="Forum Host LLM模型名称"
        )
        
        KEYWORD_OPTIMIZER_API_KEY: Optional[str] = Field(
            default=app_config.openai_api_key,
            description="Keyword Optimizer LLM API密钥"
        )
        KEYWORD_OPTIMIZER_BASE_URL: Optional[str] = Field(
            default=os.getenv("KEYWORD_OPTIMIZER_BASE_URL", "https://api.openai.com/v1"),
            description="Keyword Optimizer BaseUrl"
        )
        KEYWORD_OPTIMIZER_MODEL_NAME: Optional[str] = Field(
            default=os.getenv("KEYWORD_OPTIMIZER_MODEL_NAME", app_config.openai_model),
            description="Keyword Optimizer LLM模型名称"
        )
        
        # 网络工具配置
        TAVILY_API_KEY: Optional[str] = Field(
            default=os.getenv("TAVILY_API_KEY"),
            description="Tavily API密钥"
        )
        
        SEARCH_TOOL_TYPE: Literal["AnspireAPI", "BochaAPI"] = Field(
            default=os.getenv("SEARCH_TOOL_TYPE", "AnspireAPI"),
            description="网络搜索工具类型"
        )
        
        BOCHA_WEB_SEARCH_API_KEY: Optional[str] = Field(
            default=os.getenv("BOCHA_WEB_SEARCH_API_KEY"),
            description="Bocha API密钥"
        )
        BOCHA_BASE_URL: Optional[str] = Field(
            default=os.getenv("BOCHA_BASE_URL", "https://api.bocha.cn/v1/ai-search"),
            description="Bocha BaseUrl"
        )
        
        ANSPIRE_API_KEY: Optional[str] = Field(
            default=os.getenv("ANSPIRE_API_KEY"),
            description="Anspire API密钥"
        )
        ANSPIRE_BASE_URL: Optional[str] = Field(
            default=os.getenv("ANSPIRE_BASE_URL", "https://plugin.anspire.cn/api/ntsearch/search"),
            description="Anspire BaseUrl"
        )
        
        # Insight Engine 搜索配置
        DEFAULT_SEARCH_HOT_CONTENT_LIMIT: int = Field(
            default=int(os.getenv("DEFAULT_SEARCH_HOT_CONTENT_LIMIT", "100")),
            description="热榜内容默认最大数"
        )
        DEFAULT_SEARCH_TOPIC_GLOBALLY_LIMIT_PER_TABLE: int = Field(
            default=int(os.getenv("DEFAULT_SEARCH_TOPIC_GLOBALLY_LIMIT_PER_TABLE", "50")),
            description="按表全局话题最大数"
        )
        DEFAULT_SEARCH_TOPIC_BY_DATE_LIMIT_PER_TABLE: int = Field(
            default=int(os.getenv("DEFAULT_SEARCH_TOPIC_BY_DATE_LIMIT_PER_TABLE", "100")),
            description="按日期话题最大数"
        )
        DEFAULT_GET_COMMENTS_FOR_TOPIC_LIMIT: int = Field(
            default=int(os.getenv("DEFAULT_GET_COMMENTS_FOR_TOPIC_LIMIT", "500")),
            description="单话题评论最大数"
        )
        DEFAULT_SEARCH_TOPIC_ON_PLATFORM_LIMIT: int = Field(
            default=int(os.getenv("DEFAULT_SEARCH_TOPIC_ON_PLATFORM_LIMIT", "200")),
            description="平台搜索话题最大数"
        )
        MAX_SEARCH_RESULTS_FOR_LLM: int = Field(
            default=int(os.getenv("MAX_SEARCH_RESULTS_FOR_LLM", "50")),
            description="供LLM用搜索结果最大数"
        )
        MAX_HIGH_CONFIDENCE_SENTIMENT_RESULTS: int = Field(
            default=int(os.getenv("MAX_HIGH_CONFIDENCE_SENTIMENT_RESULTS", "100")),
            description="高置信度情感分析最大数"
        )
        
        # Database配置
        DB_DIALECT: str = Field(
            default=os.getenv("DB_DIALECT", "postgresql"),
            description="数据库类型"
        )
        DB_HOST: str = Field(
            default=os.getenv("DB_HOST", "localhost"),
            description="数据库主机"
        )
        DB_PORT: int = Field(
            default=int(os.getenv("DB_PORT", "5432")),
            description="数据库端口"
        )
        DB_USER: str = Field(
            default=os.getenv("DB_USER", "postgres"),
            description="数据库用户名"
        )
        DB_PASSWORD: str = Field(
            default=os.getenv("DB_PASSWORD", ""),
            description="数据库密码"
        )
        DB_NAME: str = Field(
            default=os.getenv("DB_NAME", "bettafish"),
            description="数据库名称"
        )
        DB_CHARSET: str = Field(
            default=os.getenv("DB_CHARSET", "utf8mb4"),
            description="数据库字符集"
        )
        
        # 搜索参数配置
        MAX_REFLECTIONS: int = Field(
            default=int(os.getenv("MAX_REFLECTIONS", "3")),
            description="最大反思次数"
        )
        MAX_PARAGRAPHS: int = Field(
            default=int(os.getenv("MAX_PARAGRAPHS", "6")),
            description="最大段落数"
        )
        SEARCH_TIMEOUT: int = Field(
            default=int(os.getenv("SEARCH_TIMEOUT", "240")),
            description="搜索超时（秒）"
        )
        MAX_CONTENT_LENGTH: int = Field(
            default=int(os.getenv("MAX_CONTENT_LENGTH", "500000")),
            description="搜索最大内容长度"
        )
        SEARCH_CONTENT_MAX_LENGTH: int = Field(
            default=int(os.getenv("SEARCH_CONTENT_MAX_LENGTH", "20000")),
            description="用于提示的最长内容长度"
        )
        MAX_SEARCH_RESULTS: int = Field(
            default=int(os.getenv("MAX_SEARCH_RESULTS", "20")),
            description="最大搜索结果数"
        )
        
        # 输出配置
        OUTPUT_DIR: str = Field(
            default=output_dir,
            description="输出目录"
        )
        SAVE_INTERMEDIATE_STATES: bool = Field(
            default=True,
            description="是否保存中间状态"
        )
        
        model_config = ConfigDict(
            env_file=".env",
            env_prefix="",
            case_sensitive=False,
            extra="allow"
        )
    
    return BettaFishSettings()
