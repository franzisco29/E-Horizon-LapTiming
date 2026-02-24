# Modules/config_manager.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

import yaml


# ----------------------------
# Dataclasses (schema config)
# ----------------------------
@dataclass
class AppConfig:
    debug: bool = True
    admin: int = 0
    first_launch: bool = True


@dataclass
class PathsConfig:
    root_path: str = str(Path.cwd() / "data")


@dataclass
class TimingConfig:
    debounce_ms: int = 3000


@dataclass
class DevicesConfig:
    connection_type: int = 0   # 0 NONE, 1 TCP, 2 LAPMONITOR, 3 WIFIUDP
    tcp_port: int = 20777
    device_available: str = "1,0,0,0,0,0"  # stringa come VB

    def device_available_flags(self, expected_len: int = 6) -> List[bool]:
        parts = [p.strip() for p in (self.device_available or "").split(",") if p.strip() != ""]
        flags = [(p == "1") for p in parts]
        if len(flags) < expected_len:
            flags += [False] * (expected_len - len(flags))
        elif len(flags) > expected_len:
            flags = flags[:expected_len]
        return flags

    def set_device_available_flags(self, flags: List[bool]) -> None:
        self.device_available = ",".join("1" if x else "0" for x in flags)


@dataclass
class LiveConfig:
    enabled: bool = True
    ip: str = "127.0.0.1"
    port: int = 8888


@dataclass
class UIConfig:
    monitor_out: int = 0


# ----------------------------
# Settings root
# ----------------------------
@dataclass
class Settings:
    app: AppConfig = field(default_factory=AppConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    timing: TimingConfig = field(default_factory=TimingConfig)
    devices: DevicesConfig = field(default_factory=DevicesConfig)
    live: LiveConfig = field(default_factory=LiveConfig)
    ui: UIConfig = field(default_factory=UIConfig)

    _path: Optional[Path] = None

    # ----------------------------
    # Convenience properties (alias stile VB)
    # ----------------------------
    @property
    def root_path(self) -> str:
        return self.paths.root_path

    @root_path.setter
    def root_path(self, value: str) -> None:
        self.paths.root_path = str(value)
        self.validate_and_fix()

    @property
    def admin(self) -> int:
        return self.app.admin

    @admin.setter
    def admin(self, value: int) -> None:
        self.app.admin = int(value)

    @property
    def debug(self) -> bool:
        return self.app.debug

    @debug.setter
    def debug(self, value: bool) -> None:
        self.app.debug = bool(value)

    @property
    def first_launch(self) -> bool:
        return self.app.first_launch

    @first_launch.setter
    def first_launch(self, value: bool) -> None:
        self.app.first_launch = bool(value)

    @property
    def debounce_ms(self) -> int:
        return self.timing.debounce_ms

    @debounce_ms.setter
    def debounce_ms(self, value: int) -> None:
        self.timing.debounce_ms = int(value)
        self.validate_and_fix()

    @property
    def connection_type(self) -> int:
        return self.devices.connection_type

    @connection_type.setter
    def connection_type(self, value: int) -> None:
        self.devices.connection_type = int(value)
        self.validate_and_fix()

    @property
    def tcp_port(self) -> int:
        return self.devices.tcp_port

    @tcp_port.setter
    def tcp_port(self, value: int) -> None:
        self.devices.tcp_port = int(value)
        self.validate_and_fix()

    @property
    def device_available(self) -> str:
        return self.devices.device_available

    @device_available.setter
    def device_available(self, value: str) -> None:
        self.devices.device_available = str(value)
        self.validate_and_fix()

    @property
    def live_enabled(self) -> bool:
        return self.live.enabled

    @live_enabled.setter
    def live_enabled(self, value: bool) -> None:
        self.live.enabled = bool(value)

    @property
    def live_ip(self) -> str:
        return self.live.ip

    @live_ip.setter
    def live_ip(self, value: str) -> None:
        self.live.ip = str(value)

    @property
    def live_port(self) -> int:
        return self.live.port

    @live_port.setter
    def live_port(self, value: int) -> None:
        self.live.port = int(value)
        self.validate_and_fix()

    @property
    def monitor_out(self) -> int:
        return self.ui.monitor_out

    @monitor_out.setter
    def monitor_out(self, value: int) -> None:
        self.ui.monitor_out = int(value)

    # ----------------------------
    # Load / Save
    # ----------------------------
    @classmethod
    def load(cls, path: Union[str, Path]) -> "Settings":
        path = Path(path)
        if not path.exists():
            cfg = cls()
            cfg._path = path
            cfg.save()
            return cfg

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        cfg = cls()
        cfg._path = path

        cfg.app.debug = bool(data.get("app", {}).get("debug", cfg.app.debug))
        cfg.app.admin = int(data.get("app", {}).get("admin", cfg.app.admin))
        cfg.app.first_launch = bool(data.get("app", {}).get("first_launch", cfg.app.first_launch))

        cfg.paths.root_path = str(data.get("paths", {}).get("root_path", cfg.paths.root_path))

        cfg.timing.debounce_ms = int(data.get("timing", {}).get("debounce_ms", cfg.timing.debounce_ms))

        cfg.devices.connection_type = int(data.get("devices", {}).get("connection_type", cfg.devices.connection_type))
        cfg.devices.tcp_port = int(data.get("devices", {}).get("tcp_port", cfg.devices.tcp_port))
        cfg.devices.device_available = str(data.get("devices", {}).get("device_available", cfg.devices.device_available))

        cfg.live.enabled = bool(data.get("live", {}).get("enabled", cfg.live.enabled))
        cfg.live.ip = str(data.get("live", {}).get("ip", cfg.live.ip))
        cfg.live.port = int(data.get("live", {}).get("port", cfg.live.port))

        cfg.ui.monitor_out = int(data.get("ui", {}).get("monitor_out", cfg.ui.monitor_out))

        cfg.validate_and_fix()
        return cfg

    def save(self, path: Union[str, Path, None] = None) -> None:
        out_path = Path(path) if path else (self._path or Path("Config/settings.yaml"))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        self._path = out_path

        payload = {
            "app": {
                "debug": self.app.debug,
                "admin": self.app.admin,
                "first_launch": self.app.first_launch,
            },
            "paths": {
                "root_path": self.paths.root_path,
            },
            "timing": {
                "debounce_ms": self.timing.debounce_ms,
            },
            "devices": {
                "connection_type": self.devices.connection_type,
                "tcp_port": self.devices.tcp_port,
                "device_available": self.devices.device_available,
            },
            "live": {
                "enabled": self.live.enabled,
                "ip": self.live.ip,
                "port": self.live.port,
            },
            "ui": {
                "monitor_out": self.ui.monitor_out,
            },
        }

        out_path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    # ----------------------------
    # Validation / normalization
    # ----------------------------
    def validate_and_fix(self) -> None:
        if self.timing.debounce_ms < 0:
            self.timing.debounce_ms = 0

        self.devices.tcp_port = _clamp_port(self.devices.tcp_port)
        self.live.port = _clamp_port(self.live.port)

        if self.devices.connection_type not in (0, 1, 2, 3):
            self.devices.connection_type = 0

        try:
            rp = Path(self.paths.root_path).expanduser()
            self.paths.root_path = str(rp)
        except Exception:
            pass

        flags = self.devices.device_available_flags(expected_len=6)
        self.devices.set_device_available_flags(flags)
        
    @staticmethod
    def default_path() -> Path:
        """
        Path di default del file settings.yaml.
        Robust: basato sulla root progetto (cartella dove sta main.py).
        """
        project_root = Path(__file__).resolve().parents[1]  # Modules/ -> project root
        return project_root / "Config" / "settings.yaml"

    @classmethod
    def load_default(cls) -> "Settings":
        """
        Carica settings dal path di default (e lo crea se non esiste).
        """
        return cls.load(cls.default_path())



def _clamp_port(port: int) -> int:
    if port < 1:
        return 1
    if port > 65535:
        return 65535
    return port
