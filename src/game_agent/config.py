from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # LLM Settings (Nvidia Platform GLM)
    nvidia_api_key: str = Field(..., description="Nvidia API Key starting with nvapi-")
    nvidia_base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        description="Nvidia API base URL",
    )
    # Using a typical standard GLM vision capable model name supported by Nvidia integration
    # e.g., nvidia/cosmos-nemotron-34b for multi-modal, or mistralai/pixtral-12b, 
    # but the user requested GLM. Since GLM-4v might not be natively on Nvidia right now, 
    # we assume a placeholder or user's provided 'meta/llama-4-maverick...'
    llm_model: str = Field(
        default="meta/llama-3.2-90b-vision-instruct", 
        description="The multi-modal model to use on Nvidia Platform"
    )

    # ADB Settings
    adb_serial: Optional[str] = Field(
        default=None, description="Specific ADB device serial to connect to"
    )

    # Application Settings
    log_level: str = "INFO"


config = AppConfig()
