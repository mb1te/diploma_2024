from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OAI_CONFIG_LIST: str

    _env_file = ".env"
