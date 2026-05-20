from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GROQ_API_KEY: str = "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"
    GOOGLE_MAPS_API_KEY: str = "AIzaSyDxiL_IxA0SED3VOpcjKUN1gzN88RqhHRo"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
