from pathlib import Path


class Settings:
    # ACBrMonitor
    acbr_host: str = "100.98.13.77"
    acbr_port: int = 3434
    acbr_timeout: int = 60

    # Certificado padrao (multiempresa futuramente no banco)
    certificado_serial: str = "69BEDD369B1C27EAD89A"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_keys: list[str] = ["nfe-dev-key"]

    # INI temp directory
    ini_dir: Path = Path("/tmp/nfe_ini")
    ini_dir.mkdir(parents=True, exist_ok=True)

    # Database (PostgreSQL - centralizador NFeHub)
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "nfehub"
    db_user: str = "nfehub"
    db_pass: str = "nfehub123"
    db_driver: str = "psycopg2"

    # SQL Server (ERP origem)
    sqlserver_host: str = "100.64.83.82"
    sqlserver_port: int = 1433
    sqlserver_db: str = "brven_brascopper"
    sqlserver_user: str = "sa"
    sqlserver_pass: str = "MULETA"
    sqlserver_driver: str = "FreeTDS"


settings = Settings()
