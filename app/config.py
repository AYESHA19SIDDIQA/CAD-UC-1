"""
Configuration management for the application
Loads settings from .env file
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # LLM Provider Selection
    llm_provider: str = Field("gemini", alias="LLM_PROVIDER")  # Options: gemini, openai, openrouter
    
    # Google Gemini Configuration
    gemini_api_key: Optional[str] = Field(None, alias="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-2.5-flash", alias="GEMINI_MODEL")
    gemini_temperature: float = Field(0.1, alias="GEMINI_TEMPERATURE")
    gemini_max_tokens: int = Field(8000, alias="GEMINI_MAX_TOKENS")
    
    # OpenAI/OpenRouter Configuration
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")
    openai_base_url: Optional[str] = Field(None, alias="OPENAI_BASE_URL")  # For OpenRouter or Azure
    openai_model: str = Field("deepseek/deepseek-v3", alias="OPENAI_MODEL")
    openai_temperature: float = Field(0, alias="OPENAI_TEMPERATURE")
    openai_max_tokens: int = Field(2000, alias="OPENAI_MAX_TOKENS")
    deepseek_small_model: str = Field("deepseek/deepseek-r1-distill-qwen-7b", alias="DEEPSEEK_SMALL_MODEL")
    qwen_small_model: str = Field("qwen/qwen2.5-7b-instruct", alias="QWEN_SMALL_MODEL")
    model_benchmark_runs: int = Field(1, alias="MODEL_BENCHMARK_RUNS")

    # Local Model Configuration (Hugging Face / CPU inference)
    local_model_name: str = Field("Qwen/Qwen2.5-1.5B-Instruct", alias="LOCAL_MODEL_NAME")
    local_temperature: float = Field(0.7, alias="LOCAL_TEMPERATURE")
    local_max_tokens: int = Field(2000, alias="LOCAL_MAX_TOKENS")
    
    
    # Application Settings
    app_name: str = Field("Document Generator", alias="APP_NAME")
    app_version: str = Field("1.0.0", alias="APP_VERSION")
    debug: bool = Field(False, alias="DEBUG")
    
    # API Settings
    api_host: str = Field("0.0.0.0", alias="API_HOST")
    api_port: int = Field(8000, alias="API_PORT")
    
    # File Upload Settings
    max_upload_size_mb: int = Field(10, alias="MAX_UPLOAD_SIZE_MB")
    allowed_file_types: str = Field(".doc,.docx,.pdf", alias="ALLOWED_FILE_TYPES")
    
    # Directory Settings
    output_dir: str = Field("./output", alias="OUTPUT_DIR")
    template_dir: str = Field("./app/templates", alias="TEMPLATE_DIR")
    
    class Config:
        # Point to .env file in document_generator root, not current working directory
        env_file = str(Path(__file__).parent.parent / ".env")
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def validate_openai_key(self) -> bool:
        """Check if OpenAI API key is configured"""
        return bool(self.openai_api_key and 
                   self.openai_api_key not in ["your_openai_api_key_here", ""])
    
    def validate_gemini_key(self) -> bool:
        """Check if Gemini API key is configured"""
        return bool(self.gemini_api_key and 
                   self.gemini_api_key not in ["your_gemini_api_key_here", ""])
    
    def validate_api_key(self) -> bool:
        """Check if API key is configured for the selected provider"""
        if self.llm_provider == "gemini":
            return self.validate_gemini_key()
        elif self.llm_provider in ["openai", "openrouter"]:
            return self.validate_openai_key()
        elif self.llm_provider == "local":
            return True  # No API key needed for local models
        return False
    
    def is_using_openrouter(self) -> bool:
        """Check if using OpenRouter"""
        return bool(self.openai_base_url and "openrouter.ai" in self.openai_base_url)
    
    def get_allowed_extensions(self) -> list:
        """Get list of allowed file extensions"""
        return [ext.strip() for ext in self.allowed_file_types.split(",")]
    
    @property
    def max_upload_size_bytes(self) -> int:
        """Get max upload size in bytes"""
        return self.max_upload_size_mb * 1024 * 1024


# Global settings instance
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """
    Get application settings (singleton pattern)
    Loads settings once and reuses the same instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

def reload_settings() -> Settings:
    """
    Force reload settings from .env file
    Useful for testing or when .env file changes
    """
    global _settings
    _settings = Settings()
    return _settings


# Quick access to settings
settings = get_settings()


if __name__ == "__main__":
    """Test configuration loading"""
    print("="*80)
    print("CONFIGURATION TEST")
    print("="*80)
    
    settings = get_settings()
    
    print(f"\nApp Name: {settings.app_name}")
    print(f"App Version: {settings.app_version}")
    print(f"Debug Mode: {settings.debug}")
    
    print(f"\nAPI Host: {settings.api_host}")
    print(f"API Port: {settings.api_port}")
    
    print(f"\nLLM Provider: {'OpenRouter' if settings.is_using_openrouter() else 'Direct OpenAI'}")
    if settings.openai_base_url:
        print(f"Base URL: {settings.openai_base_url}")
    print(f"Model: {settings.openai_model}")
    print(f"Temperature: {settings.openai_temperature}")
    print(f"Max Tokens: {settings.openai_max_tokens}")
    
    # Don't print the actual API key, just check if it's configured
    if settings.validate_openai_key():
        print(f"API Key: ✅ Configured (***{settings.openai_api_key[-4:]})")
    else:
        print(f"API Key: ❌ Not configured or using example value")
    
    print(f"\nMax Upload Size: {settings.max_upload_size_mb} MB ({settings.max_upload_size_bytes:,} bytes)")
    print(f"Allowed File Types: {settings.get_allowed_extensions()}")
    
    print(f"\nOutput Directory: {settings.output_dir}")
    print(f"Template Directory: {settings.template_dir}")
    
    print("\n" + "="*80)
    
    if not settings.validate_openai_key():
        print("\n⚠️  WARNING: API key not configured!")
        print("   1. Copy .env.example to .env")
        print("   2. Edit .env and add your API key")
        print("   3. Never commit .env to git (it's in .gitignore)")
