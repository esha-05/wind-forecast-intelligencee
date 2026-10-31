import os


class Settings:
    elexon_base = os.getenv("ELEXON_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1")
    default_cutoff = os.getenv("DEFAULT_CUTOFF", "08:00")  # HH:MM UTC on day D-1 (ASSUMPTION)
    cors = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]
    cache_ttl = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    chunk_days = int(os.getenv("CHUNK_DAYS", "7"))
    timeout = float(os.getenv("HTTP_TIMEOUT_SECONDS", "30"))


settings = Settings()
