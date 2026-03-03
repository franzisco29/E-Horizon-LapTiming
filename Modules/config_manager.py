# Modules/config_manager.py
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

import yaml

from Modules.paths import create_required_folders


# ----------------------------
# App identity (Windows AppData folder)
# ----------------------------
APP_NAME = "E-Horizon-LapTiming"  # <-- cambia qui se vuoi


def _win_appdata_dir(app_name: str = APP_NAME) -> Path:
    """
    Directory scrivibile utente per stato/config (Windows).
    Esempio: C:\\Users\\<user>\\AppData\\Roaming\\<app_name>
    """
    appdata = os.environ.get("APPDATA")  # Roaming
    if not appdata:
        return Path.home() / app_name
    return Path(appdata) / app_name


def _locator_path() -> Path:
    """
    File che memorizza la posizione del vero settings.yaml.
    """
    return _win_appdata_dir(APP_NAME) / "settings_path.txt"


# ----------------------------
# Dataclasses (schema config)
# ----------------------------
@dataclass
class AppConfig:
    debug: bool = True
    admin: int = 1
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
    timing_enabled: bool = True
    tv_enabled: bool = False
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
        return self.live.timing_enabled

    @live_enabled.setter
    def live_enabled(self, value: bool) -> None:
        self.live.timing_enabled = bool(value)

    @property
    def timing_enabled(self) -> bool:
        return self.live.timing_enabled

    @timing_enabled.setter
    def timing_enabled(self, value: bool) -> None:
        self.live.timing_enabled = bool(value)

    @property
    def tv_enabled(self) -> bool:
        return self.live.tv_enabled

    @tv_enabled.setter
    def tv_enabled(self, value: bool) -> None:
        self.live.tv_enabled = bool(value)

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
    # Defaults (single source of truth)
    # ----------------------------
    @classmethod
    def default(cls) -> "Settings":
        """
        Default ufficiali del progetto (modifica qui i tuoi default reali).
        """
        return cls(
            app=AppConfig(debug=True, admin=1, first_launch=True),
            # paths.root_path verrà impostato al primo avvio su <base>/Settings
            timing=TimingConfig(debounce_ms=3000),
            devices=DevicesConfig(connection_type=0, tcp_port=20777, device_available="1,0,0,0,0,0"),
            live=LiveConfig(timing_enabled=True, tv_enabled=False, ip="127.0.0.1", port=8888),
            ui=UIConfig(monitor_out=0),
        )

    # ----------------------------
    # Load / Save
    # ----------------------------
    @classmethod
    def load(cls, path: Union[str, Path]) -> "Settings":
        path = Path(path)

        if not path.exists():
            cfg = cls.default()
            cfg._path = path
            cfg.save(path)
            return cfg

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        cfg = cls.default()
        cfg._path = path

        cfg.app.debug = bool(data.get("app", {}).get("debug", cfg.app.debug))
        cfg.app.admin = int(data.get("app", {}).get("admin", cfg.app.admin))
        cfg.app.first_launch = bool(data.get("app", {}).get("first_launch", cfg.app.first_launch))

        cfg.paths.root_path = str(data.get("paths", {}).get("root_path", cfg.paths.root_path))

        cfg.timing.debounce_ms = int(data.get("timing", {}).get("debounce_ms", cfg.timing.debounce_ms))

        cfg.devices.connection_type = int(data.get("devices", {}).get("connection_type", cfg.devices.connection_type))
        cfg.devices.tcp_port = int(data.get("devices", {}).get("tcp_port", cfg.devices.tcp_port))
        cfg.devices.device_available = str(data.get("devices", {}).get("device_available", cfg.devices.device_available))

        # compatibility: support several possible key names for the new flags
        live_section = data.get("live", {}) or {}
        cfg.live.timing_enabled = bool(
            live_section.get("timing_enabled", live_section.get("Timing_enabled", live_section.get("enabled", cfg.live.timing_enabled)))
        )
        cfg.live.tv_enabled = bool(
            live_section.get("tv_enabled", live_section.get("tv_Enabled", cfg.live.tv_enabled))
        )
        cfg.live.ip = str(data.get("live", {}).get("ip", cfg.live.ip))
        cfg.live.port = int(data.get("live", {}).get("port", cfg.live.port))

        cfg.ui.monitor_out = int(data.get("ui", {}).get("monitor_out", cfg.ui.monitor_out))

        cfg.validate_and_fix()
        return cfg

    def save(self, path: Union[str, Path, None] = None) -> None:
        out_path = Path(path) if path else (self._path or Path("settings.yaml"))
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
                "timing_enabled": self.live.timing_enabled,
                "tv_enabled": self.live.tv_enabled,
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

    # ----------------------------
    # Windows first-run: dialog + AppData locator
    # ----------------------------
    @classmethod
    def load_default(cls) -> "Settings":
        """
        Windows:
        - Se esiste il locator in %APPDATA%\\<APP_NAME>\\settings_path.txt, carica da lì.
        - Altrimenti: primo avvio -> dialog per scegliere dove creare "Settings".
          Crea Settings\\settings.yaml e cartelle richieste, salva e scrive locator.
        """
        # 1) prova a risolvere dal locator (exe-safe)
        state_dir = _win_appdata_dir(APP_NAME)
        state_dir.mkdir(parents=True, exist_ok=True)
        locator = _locator_path()

        if locator.exists():
            saved = (locator.read_text(encoding="utf-8") or "").strip()
            if saved:
                p = Path(saved).expanduser()
                if p.exists():
                    return cls.load(p)

        # 2) primo avvio: chiedi cartella base
        base_dir = _pick_base_dir_windows()
        if base_dir is None:
            # fallback: crea in AppData se l'utente annulla
            base_dir = state_dir

        settings_dir = base_dir / "Settings"
        settings_file = settings_dir / "settings.yaml"

        first_time = not settings_file.exists()
        cfg = cls.load(settings_file)

        if first_time:
            # IMPORTANT: root_path deve essere Settings_dir
            cfg.root_path = str(base_dir)

            create_required_folders(base_dir, force_creation=True)

            cfg.first_launch = False
            cfg.save(settings_file)

        # 3) salva locator
        locator.write_text(str(settings_file), encoding="utf-8")

        return cfg

    @classmethod
    def reset_settings_location(cls) -> None:
        """
        Cancella il locator in AppData: al prossimo avvio verrà richiesto di nuovo il percorso.
        """
        loc = _locator_path()
        try:
            if loc.exists():
                loc.unlink()
        except Exception:
            pass


def _pick_base_dir_windows() -> Optional[Path]:
    """
    Apre una dialog Windows per scegliere una cartella base.
    Ritorna None se annullato o se Tk non è disponibile.
    """
    try:
        from tkinter import Tk, filedialog  # import locale per evitare problemi in ambienti headless

        root = Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        chosen = filedialog.askdirectory(title="Scegli dove creare la cartella Settings")
        root.destroy()

        if not chosen:
            return None
        return Path(chosen).expanduser().resolve()
    except Exception:
        return None


def _clamp_port(port: int) -> int:
    if port < 1:
        return 1
    if port > 65535:
        return 65535
    return port