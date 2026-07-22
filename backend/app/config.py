from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://codesync:codesync@localhost:5432/codesync"
    redis_url: str = "redis://localhost:6379/0"

    github_client_id: str = ""
    github_client_secret: str = ""
    github_oauth_redirect_uri: str = "http://localhost:8000/auth/github/callback"

    frontend_url: str = "http://localhost:5173"

    jwt_secret: str = "change_me_to_a_long_random_string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080

    max_collaborators_per_session: int = 10


settings = Settings()
