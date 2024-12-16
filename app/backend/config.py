from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import ClassVar
import os


class Settings(BaseSettings):
    IN_AZURE: ClassVar[bool] = os.getenv("AZURE_CLIENT_ID") is not None

    def get_credential(self):
        if self.IN_AZURE:
            return ManagedIdentityCredential()
        return DefaultAzureCredential()

    CONNECTION_STRING: str
    AZURE_SEARCH_INDEX: str = "product-vector-index"
    MODEL_NAME: str = "gpt-4o-mini"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
