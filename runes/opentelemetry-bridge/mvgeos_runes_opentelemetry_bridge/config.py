from __future__ import annotations

import json
import os
from pathlib import Path

from mvgeos_runes_opentelemetry_bridge.types import OTelConfig


def load_otel_config(
    cwd: Path | None = None,
    global_dir: Path | None = None,
) -> OTelConfig:
    """Load OpenTelemetry configuration from global and project otel.json files,

    falling back to standard OTEL environment variables.
    """
    config = OTelConfig()

    # 1. Global config (~/.agents/otel.json or global_dir / "otel.json")
    g_dir = global_dir or (Path.home() / ".agents")
    global_file = g_dir / "otel.json"
    if global_file.is_file():
        try:
            with global_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            _apply_dict_config(config, data)
        except (json.JSONDecodeError, OSError):
            pass

    # 2. Project config (<project>/.agents/otel.json)
    if cwd is not None:
        proj_file = cwd / ".agents" / "otel.json"
        if proj_file.is_file():
            try:
                with proj_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                _apply_dict_config(config, data)
            except (json.JSONDecodeError, OSError):
                pass

    # 3. Environment variables (highest precedence)
    env_service = os.getenv("OTEL_SERVICE_NAME")
    if env_service:
        config.service_name = env_service

    env_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if env_endpoint:
        config.endpoint = env_endpoint

    env_disabled = os.getenv("OTEL_SDK_DISABLED", "").lower()
    if env_disabled in ("true", "1", "yes"):
        config.disabled = True

    env_in_memory = os.getenv("MVGEOS_OTEL_IN_MEMORY", "").lower()
    if env_in_memory in ("true", "1", "yes"):
        config.in_memory = True

    return config


def _apply_dict_config(config: OTelConfig, data: dict) -> None:
    if "service_name" in data and isinstance(data["service_name"], str):
        config.service_name = data["service_name"]
    if "endpoint" in data and isinstance(data["endpoint"], str):
        config.endpoint = data["endpoint"]
    if "headers" in data and isinstance(data["headers"], dict):
        config.headers.update(data["headers"])
    if "in_memory" in data and isinstance(data["in_memory"], bool):
        config.in_memory = data["in_memory"]
    if "disabled" in data and isinstance(data["disabled"], bool):
        config.disabled = data["disabled"]
