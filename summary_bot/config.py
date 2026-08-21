from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    dashscope_api_key: str
    admin_user_id: int = 127626487
    database_path: str = "/app/data/bot.db"
    qwen_model: str = "qwen3.5-flash"
    dashscope_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    tz: str = "Europe/Moscow"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
