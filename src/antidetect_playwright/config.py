"""Configuration loader."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomllib


@dataclass(frozen=True)
class BrowserConfig:
    """Browser configuration."""

    type: str
    max_contexts: int
    context_timeout: int
    page_timeout: int
    headless: bool
    executable_path: str
    user_data_dir: str
    downloads_dir: str


@dataclass(frozen=True)
class StealthConfig:
    """Stealth mode configuration."""

    enabled: bool
    hide_webdriver: bool
    randomize_navigator: bool
    canvas_protection: bool
    webgl_protection: bool
    audio_protection: bool
    client_rects_protection: bool
    human_timing: bool


@dataclass(frozen=True)
class FingerprintConfig:
    """Fingerprint generation configuration."""

    screen_resolutions: tuple[dict[str, int], ...]
    languages: tuple[str, ...]
    timezones: tuple[str, ...]
    platforms: tuple[str, ...]


@dataclass(frozen=True)
class ProxyConfig:
    """Proxy configuration."""

    rotation_enabled: bool
    rotation_strategy: str
    validation_timeout: int
    max_retries: int
    retry_delay: int
    list_file: str


@dataclass(frozen=True)
class TaskRunnerConfig:
    """Task runner configuration."""

    max_concurrent_tasks: int
    task_timeout: int
    retry_on_failure: bool
    max_task_retries: int
    queue_size: int


@dataclass(frozen=True)
class RedisConfig:
    """Redis configuration."""

    host: str
    port: int
    password: str | None
    db: int
    pool_size: int
    key_prefix: str
    default_ttl: int
    connection_timeout: int


@dataclass(frozen=True)
class StorageConfig:
    """Storage paths configuration."""

    data_dir: str
    logs_dir: str
    screenshots_dir: str
    scripts_dir: str
    results_dir: str


@dataclass(frozen=True)
class LoggingConfig:
    """Logging configuration."""

    level: str
    format: str
    date_format: str
    console: bool
    file: bool
    json: bool
    max_size_mb: int
    backup_count: int
    compress: bool


@dataclass(frozen=True)
class GuiConfig:
    """GUI configuration."""

    default_width: int
    default_height: int
    min_width: int
    min_height: int
    sidebar_width: int
    items_per_page: int
    theme: str
    enable_chrome_theme: bool
    data_dir: str
    browser_data_dir: str
    settings_file: str
    profiles_file: str


@dataclass(frozen=True)
class SessionConfig:
    """Session configuration."""

    max_uniqueness_attempts: int


@dataclass(frozen=True)
class HumanBehaviorConfig:
    """Human behavior simulation configuration."""

    delay_min_ms: int
    delay_max_ms: int
    scroll_min_px: int
    scroll_max_px: int


@dataclass(frozen=True)
class ServerConfig:
    """Server configuration."""

    host: str
    port: int


@dataclass(frozen=True)
class AppConfig:
    """Complete application configuration."""

    name: str
    version: str
    environment: str
    server: ServerConfig
    browser: BrowserConfig
    stealth: StealthConfig
    fingerprint: FingerprintConfig
    proxy: ProxyConfig
    task_runner: TaskRunnerConfig
    redis: RedisConfig
    storage: StorageConfig
    logging: LoggingConfig
    gui: GuiConfig
    session: SessionConfig
    human_behavior: HumanBehaviorConfig


def _get_env_override(section: str, key: str) -> str | None:
    """Get environment variable override."""
    env_key = f"APP_{section.upper()}_{key.upper()}"
    return os.environ.get(env_key)


def _apply_overrides(data: dict, section: str) -> dict:
    """Apply environment variable overrides to section."""
    result = dict(data)
    for key in result:
        override = _get_env_override(section, key)
        if override is not None:
            if isinstance(result[key], bool):
                result[key] = override.lower() in ("true", "1", "yes")
            elif isinstance(result[key], int):
                result[key] = int(override)
            else:
                result[key] = override
    return result


def load_config(config_dir: str | Path) -> AppConfig:
    """Load configuration from TOML files.

    Args:
        config_dir: Path to configuration directory.

    Returns:
        Complete application configuration.

    Raises:
        FileNotFoundError: If required config file is missing.
        ValueError: If required configuration value is missing.
    """
    config_path = Path(config_dir)

    app_path = config_path / "app.toml"
    runtime_path = config_path / "runtime.toml"
    logging_path = config_path / "logging.toml"

    for path in (app_path, runtime_path, logging_path):
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(app_path, "rb") as f:
        app_data = tomllib.load(f)

    with open(runtime_path, "rb") as f:
        runtime_data = tomllib.load(f)

    with open(logging_path, "rb") as f:
        logging_data = tomllib.load(f)

    browser_data = {**app_data["browser"], **runtime_data.get("browser", {})}
    browser_data = _apply_overrides(browser_data, "browser")

    proxy_data = {**app_data["proxy"], **runtime_data.get("proxy", {})}
    proxy_data = _apply_overrides(proxy_data, "proxy")

    redis_data = {**app_data["redis"], **runtime_data.get("redis", {})}
    redis_data = _apply_overrides(redis_data, "redis")
    redis_data["password"] = os.environ.get("APP_REDIS_PASSWORD") or None

    server_data = _apply_overrides(runtime_data["server"], "server")
    storage_data = _apply_overrides(runtime_data["storage"], "storage")
    scripts_data = _apply_overrides(runtime_data["scripts"], "scripts")

    logging_section = _apply_overrides(logging_data["logging"], "logging")
    logging_handlers = logging_data["logging"]["handlers"]
    logging_rotation = logging_data["logging"]["rotation"]

    return AppConfig(
        name=app_data["application"]["name"],
        version=app_data["application"]["version"],
        environment=app_data["application"]["environment"],
        server=ServerConfig(
            host=server_data["host"],
            port=server_data["port"],
        ),
        browser=BrowserConfig(
            type=browser_data["type"],
            max_contexts=browser_data["max_contexts"],
            context_timeout=browser_data["context_timeout"],
            page_timeout=browser_data["page_timeout"],
            headless=browser_data["headless"],
            executable_path=browser_data.get("executable_path", ""),
            user_data_dir=browser_data["user_data_dir"],
            downloads_dir=browser_data["downloads_dir"],
        ),
        stealth=StealthConfig(
            enabled=app_data["stealth"]["enabled"],
            hide_webdriver=app_data["stealth"]["hide_webdriver"],
            randomize_navigator=app_data["stealth"]["randomize_navigator"],
            canvas_protection=app_data["stealth"]["canvas_protection"],
            webgl_protection=app_data["stealth"]["webgl_protection"],
            audio_protection=app_data["stealth"]["audio_protection"],
            client_rects_protection=app_data["stealth"]["client_rects_protection"],
            human_timing=app_data["stealth"]["human_timing"],
        ),
        fingerprint=FingerprintConfig(
            screen_resolutions=tuple(app_data["fingerprint"]["screen_resolutions"]),
            languages=tuple(app_data["fingerprint"]["languages"]),
            timezones=tuple(app_data["fingerprint"]["timezones"]),
            platforms=tuple(app_data["fingerprint"]["platforms"]),
        ),
        proxy=ProxyConfig(
            rotation_enabled=proxy_data["rotation_enabled"],
            rotation_strategy=proxy_data["rotation_strategy"],
            validation_timeout=proxy_data["validation_timeout"],
            max_retries=proxy_data["max_retries"],
            retry_delay=proxy_data["retry_delay"],
            list_file=proxy_data["list_file"],
        ),
        task_runner=TaskRunnerConfig(
            max_concurrent_tasks=app_data["task_runner"]["max_concurrent_tasks"],
            task_timeout=app_data["task_runner"]["task_timeout"],
            retry_on_failure=app_data["task_runner"]["retry_on_failure"],
            max_task_retries=app_data["task_runner"]["max_task_retries"],
            queue_size=app_data["task_runner"]["queue_size"],
        ),
        redis=RedisConfig(
            host=redis_data["host"],
            port=redis_data["port"],
            password=redis_data["password"],
            db=redis_data["db"],
            pool_size=redis_data["pool_size"],
            key_prefix=redis_data["key_prefix"],
            default_ttl=redis_data["default_ttl"],
            connection_timeout=redis_data["connection_timeout"],
        ),
        storage=StorageConfig(
            data_dir=storage_data["data_dir"],
            logs_dir=storage_data["logs_dir"],
            screenshots_dir=storage_data["screenshots_dir"],
            scripts_dir=scripts_data["scripts_dir"],
            results_dir=scripts_data["results_dir"],
        ),
        logging=LoggingConfig(
            level=logging_section["level"],
            format=logging_section["format"],
            date_format=logging_section["date_format"],
            console=logging_handlers["console"],
            file=logging_handlers["file"],
            json=logging_handlers["json"],
            max_size_mb=logging_rotation["max_size_mb"],
            backup_count=logging_rotation["backup_count"],
            compress=logging_rotation["compress"],
        ),
        gui=GuiConfig(
            default_width=app_data["gui"]["default_width"],
            default_height=app_data["gui"]["default_height"],
            min_width=app_data["gui"]["min_width"],
            min_height=app_data["gui"]["min_height"],
            sidebar_width=app_data["gui"]["sidebar_width"],
            items_per_page=app_data["gui"]["items_per_page"],
            theme=app_data["gui"]["theme"],
            enable_chrome_theme=app_data["gui"]["enable_chrome_theme"],
            data_dir=app_data["gui"]["data_dir"],
            browser_data_dir=app_data["gui"]["browser_data_dir"],
            settings_file=app_data["gui"]["settings_file"],
            profiles_file=app_data["gui"]["profiles_file"],
        ),
        session=SessionConfig(
            max_uniqueness_attempts=app_data["session"]["max_uniqueness_attempts"],
        ),
        human_behavior=HumanBehaviorConfig(
            delay_min_ms=app_data["human_behavior"]["delay_min_ms"],
            delay_max_ms=app_data["human_behavior"]["delay_max_ms"],
            scroll_min_px=app_data["human_behavior"]["scroll_min_px"],
            scroll_max_px=app_data["human_behavior"]["scroll_max_px"],
        ),
    )
