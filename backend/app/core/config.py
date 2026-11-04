from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "LocalPDF API"
    max_upload_mb: int = 200
    temp_ttl_minutes: int = 30
    temp_root: str = "/tmp/localpdf"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings = Settings()
