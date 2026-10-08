from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    environment: str = "development"
    port: int = 8000
    database_url: str = "sqlite+aiosqlite:///trading_bot.db"
    
    admin_api_key: str = "dev_key"
    
    crypto_exchange: str = "binance"
    twelve_data_api_key: str = ""
    oanda_api_key: str = ""
    
    ai_provider: str = "openai"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    ai_model: str = "gpt-4o"
    ai_weight: float = 0.6
    min_probability_threshold: int = 75
    
    min_rr: float = 2.0
    mss_lookback_candles: int = 10
    displacement_atr_multiplier: float = 1.5
    scan_interval_seconds: int = 300
    
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    alert_recipient_email: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
