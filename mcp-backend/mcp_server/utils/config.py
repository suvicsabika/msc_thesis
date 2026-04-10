from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "mcp-backend"
    debug: bool = True

    base_dir: Path = Path(__file__).resolve().parents[2]
    storage_dir: Path = base_dir / "mcp_server" / "storage"
    raw_dir: Path = storage_dir / "raw"
    processed_dir: Path = storage_dir / "processed"
    resources_dir: Path = storage_dir / "resources"
    temp_dir: Path = storage_dir / "temp"

    mcp_transport: str = "stdio"  # "stdio" or "http"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 9000

    bridge_host: str = "127.0.0.1"
    bridge_port: int = 8000

    # Debug-related
    debug_visualize: bool = False
    debug_save_annotated_video: bool = True
    debug_save_debug_json: bool = True
    debug_window_delay_ms: int = 50

    debug_step_mode: bool = True
    debug_preview_max_width: int = 1600
    debug_preview_max_height: int = 900
    debug_minimap_zoom: float = 3.0

    # Video analysis tuning
    sample_period_sec: float = 1.0
    max_video_seconds: int = 600
    position_emit_cooldown_sec: float = 3.0

    # ROI thresholds
    kill_change_threshold: float = 0.10
    plant_change_threshold: float = 0.08
    ace_change_threshold: float = 0.10

    kill_cooldown_sec: float = 1.5
    plant_cooldown_sec: float = 8.0
    ace_cooldown_sec: float = 10.0


settings = Settings()

for folder in [
    settings.storage_dir,
    settings.raw_dir,
    settings.processed_dir,
    settings.resources_dir,
    settings.temp_dir,
]:
    folder.mkdir(parents=True, exist_ok=True)