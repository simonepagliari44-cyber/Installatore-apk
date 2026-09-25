#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import importlib
import math
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

gi: Any
Adw: Any
Gdk: Any
Gio: Any
GLib: Any
Gtk: Any
Pango: Any
GI_IMPORT_ERROR: Any

DOWNLOAD_IMAGE_NAMES = ("download.svg", "download.png")
LINE_CAP_ROUND = 1
LINE_JOIN_ROUND = 1
DOWNLOAD_COLOR = (230 / 255, 97 / 255, 0 / 255)

try:
    gi = importlib.import_module("gi")
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    Adw = importlib.import_module("gi.repository.Adw")
    Gdk = importlib.import_module("gi.repository.Gdk")
    Gio = importlib.import_module("gi.repository.Gio")
    GLib = importlib.import_module("gi.repository.GLib")
    Gtk = importlib.import_module("gi.repository.Gtk")
    Pango = importlib.import_module("gi.repository.Pango")
except (ImportError, ValueError, AttributeError) as error:
    gi = None
    Adw = None
    Gdk = None
    Gio = None
    GLib = None
    Gtk = None
    Pango = None
    GI_IMPORT_ERROR = error
else:
    GI_IMPORT_ERROR = None


_ApplicationBase: Any
_ApplicationWindowBase: Any

if gi is None:
    class _UnavailableGtkBase:
        pass

    _ApplicationBase = _UnavailableGtkBase
    _ApplicationWindowBase = _UnavailableGtkBase
else:
    _ApplicationBase = Adw.Application
    _ApplicationWindowBase = Adw.ApplicationWindow


APP_ID = "com.simonecompany.installatoreapk"
APP_TITLE = "Installatore Apk"
APP_ICON_NAME = "installatore-apk"
APP_ICON_FALLBACK = "application-x-executable-symbolic"
PERMISSION_PREFIX = "android.permission."


def _app_version() -> str:
    for candidate in (
        Path(__file__).resolve().parent / "VERSION",
        Path("/usr/share/installatore-apk/VERSION"),
    ):
        try:
            text = candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if text:
            return f"v{text}"
    return "sviluppo"


def _asset_path(name: str) -> Optional[str]:
    candidates = (
        Path(__file__).resolve().parent / "data" / name,
        Path("/usr/share/installatore-apk") / name,
        Path("/usr/share/icons/hicolor/scalable/apps") / name,
    )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def _load_texture(path: str) -> Any:
    try:
        return Gdk.Texture.new_from_file(path)
    except Exception:
        return None


def _set_image_from_asset(image: Any, name: str) -> bool:
    path = _asset_path(name)
    if path is None:
        return False
    texture = _load_texture(path)
    if texture is None:
        return False
    try:
        image.set_from_paintable(texture)
        return True
    except Exception:
        return False


def _set_app_image(image: Any) -> None:
    if _set_image_from_asset(image, "installatore-apk.svg"):
        return
    try:
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        if theme.has_icon(APP_ICON_NAME):
            image.set_from_icon_name(APP_ICON_NAME)
            return
    except Exception:
        pass
    image.set_from_icon_name(APP_ICON_FALLBACK)


@dataclass
class ApkInfo:
    path: str
    name: str
    package: str
    version_name: str
    version_code: str
    permissions: List[str]
    icon_path: Optional[str] = None
    temporary_directory: Optional[Any] = None

    def dispose(self) -> None:
        if self.temporary_directory is not None:
            self.temporary_directory.cleanup()
            self.temporary_directory = None
        self.icon_path = None


@dataclass(frozen=True)
class AdbDevice:
    serial: str
    state: str
    model: Optional[str] = None
    product: Optional[str] = None

    @property
    def is_ready(self) -> bool:
        return self.state == "device"

    @property
    def display_name(self) -> str:
        if self.model:
            return f"{self.model.replace('_', ' ')} · {self.serial}"
        return self.serial


class CommandError(RuntimeError):
    pass


def run_command(
    command: Sequence[str], timeout: Optional[int] = None
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            list(command),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except FileNotFoundError as error:
        raise CommandError(f"Comando non trovato: {command[0]}") from error
    except subprocess.TimeoutExpired as error:
        raise CommandError(f"Operazione scaduta: {command[0]}") from error
    except OSError as error:
        raise CommandError(
            f"Impossibile eseguire {command[0]}: {error}"
        ) from error


class AdbClient:
    def __init__(self, executable: Optional[str] = None) -> None:
        candidate = executable or os.environ.get("ADB") or "adb"
        resolved = shutil.which(candidate)
        if resolved is None and os.path.isfile(candidate):
            resolved = os.path.abspath(candidate)
        self.executable = resolved

    def _base_command(self, serial: Optional[str] = None) -> List[str]:
        if not self.executable:
            raise CommandError(
                "ADB non è installato oppure non è disponibile nel PATH."
            )
        command = [self.executable]
        if serial:
            command.extend(["-s", serial])
        return command

    def discover_devices(self) -> List[AdbDevice]:
        result = run_command(
            self._base_command() + ["devices", "-l"], timeout=15
        )
        if result.returncode != 0:
            detail = self._format_error(result.stderr or result.stdout)
            raise CommandError(f"Impossibile interrogare ADB. {detail}")

        devices: List[AdbDevice] = []
        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("List of devices attached"):
                continue
            if line.startswith("*") or line.lower().startswith("adb:"):
                continue
            fields = line.split()
            if len(fields) < 2:
                continue
            serial, state = fields[0], fields[1]
            if not serial or serial in {"error", "daemon"}:
                continue
            properties: Dict[str, str] = {}
            for field in fields[2:]:
                if ":" not in field:
                    continue
                key, value = field.split(":", 1)
                properties[key] = value
            devices.append(
                AdbDevice(
                    serial=serial,
                    state=state,
                    model=properties.get("model"),
                    product=properties.get("product"),
                )
            )
        return devices

    def install_apk(
        self,
        device: AdbDevice,
        apk_path: str,
        on_output: Optional[Callable[[str], None]] = None,
        on_process: Optional[
            Callable[[Optional[subprocess.Popen]], None]
        ] = None,
        timeout: int = 600,
    ) -> str:
        command = self._base_command(device.serial) + [
            "install",
            "-r",
            apk_path,
        ]
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except OSError as error:
            raise CommandError(f"Impossibile avviare ADB: {error}") from error

        if on_process is not None:
            on_process(process)
        try:
            output, _ = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as error:
            try:
                process.kill()
            except OSError:
                pass
            remaining_output, _ = process.communicate()
            detail = self._format_error(remaining_output)
            raise CommandError(
                f"Installazione scaduta dopo {timeout} secondi. {detail}"
            ) from error
        finally:
            if on_process is not None:
                on_process(None)

        cleaned_output = (output or "").strip()
        if on_output is not None and cleaned_output:
            for line in cleaned_output.splitlines():
                cleaned = line.strip()
                if cleaned:
                    on_output(cleaned)
        if process.returncode != 0:
            detail = self._format_error(cleaned_output)
            raise CommandError(f"Installazione non riuscita. {detail}")
        return cleaned_output

    def launch_package(self, device: AdbDevice, package: str) -> str:
        command = self._base_command(device.serial) + [
            "shell",
            "monkey",
            "-p",
            package,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        ]
        result = run_command(command, timeout=45)
        if result.returncode != 0:
            detail = self._format_error(result.stderr or result.stdout)
            raise CommandError(
                f"Applicazione installata, ma avvio non riuscito. {detail}"
            )
        return result.stdout.strip()

    @staticmethod
    def _format_error(output: str) -> str:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if not lines:
            return "Nessun dettaglio disponibile."
        return "\n".join(lines[-6:])[:1200]


def _unquote_apk_value(value: str) -> str:
    value = value.strip()
    if (
        len(value) >= 2
        and value[0] in {"'", '"', "`"}
        and value[-1] == value[0]
    ):
        value = value[1:-1]
    return value.replace("\\'", "'").replace('\\"', '"').replace("\\`", "`")


def _assignment_value(line: str, key: str) -> Optional[str]:
    pattern = re.compile(
        rf"\b{re.escape(key)}\s*=\s*(?:(['\"])(.*?)\1|([^\s]+))"
    )
    match = pattern.search(line)
    if not match:
        return None
    return _unquote_apk_value(match.group(2) or match.group(3) or "")


def _label_from_line(line: str) -> Optional[str]:
    _, separator, value = line.partition(":")
    if not separator:
        return None
    value = _unquote_apk_value(value)
    return value or None


def _parse_badging(output: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "name": None,
        "package": None,
        "version_name": None,
        "version_code": None,
        "permissions": [],
        "icon": None,
    }
    permissions: List[str] = []

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if line.startswith("package:"):
            result["package"] = _assignment_value(line, "name")
            result["version_code"] = _assignment_value(line, "versionCode")
            result["version_name"] = _assignment_value(line, "versionName")
        elif line.startswith("application-label:"):
            label = _label_from_line(line)
            if label and not result["name"]:
                result["name"] = label
        elif line.startswith("application:"):
            result["icon"] = _assignment_value(line, "icon")
            if not result["name"]:
                result["name"] = _assignment_value(line, "label")
        elif line.startswith("uses-permission"):
            permission = _assignment_value(line, "name")
            if permission and permission not in permissions:
                permissions.append(permission)

    result["permissions"] = permissions
    return result


def _safe_parser_call(parser: Any, method_names: Sequence[str]) -> Any:
    for method_name in method_names:
        method = getattr(parser, method_name, None)
        if not callable(method):
            continue
        try:
            value = method()
        except Exception:
            continue
        if value not in (None, ""):
            return value
    return None


def _parser_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (str, int, float)):
        return str(value)
    return None


def _parse_with_pyaxmlparser(apk_path: str) -> Optional[Dict[str, Any]]:
    try:
        pyaxmlparser = importlib.import_module("pyaxmlparser")
        APK = pyaxmlparser.APK
    except (ImportError, AttributeError):
        return None

    try:
        parser = APK(apk_path)
        package = _parser_text(_safe_parser_call(parser, ("get_package",)))
        if not package:
            return None
        raw_permissions = _safe_parser_call(parser, ("get_permissions",)) or []
        permissions: List[str] = []
        if isinstance(raw_permissions, dict):
            raw_permissions = list(raw_permissions.values())
        for item in raw_permissions:
            value = None
            if isinstance(item, dict):
                value = item.get("name") or item.get("permission")
            else:
                value = _parser_text(item)
            if value and value not in permissions:
                permissions.append(str(value))
        icon = _parser_text(
            _safe_parser_call(parser, ("get_icon", "get_app_icon"))
        )
        return {
            "name": _parser_text(_safe_parser_call(parser, ("get_app_name",))),
            "package": package,
            "version_name": _parser_text(
                _safe_parser_call(
                    parser, ("get_androidversion_name", "get_version_name")
                )
            ),
            "version_code": _parser_text(
                _safe_parser_call(
                    parser, ("get_androidversion_code", "get_version_code")
                )
            ),
            "permissions": permissions,
            "icon": icon,
        }
    except Exception:
        return None


def _zip_icon_candidates(apk_path: str, icon_hint: Optional[str]) -> List[str]:
    try:
        with zipfile.ZipFile(apk_path, "r") as archive:
            names = archive.namelist()
    except (OSError, zipfile.BadZipFile):
        return []

    candidates: List[str] = []
    if icon_hint:
        hint = icon_hint.replace("\\", "/")
        for candidate in (hint, hint.lstrip("./")):
            if candidate in names and candidate not in candidates:
                candidates.append(candidate)

    prioritized = [
        name
        for name in names
        if "ic_launcher" in name.lower()
        and name.lower().endswith((".png", ".webp", ".jpg", ".jpeg"))
    ]
    fallback = [
        name
        for name in names
        if name.lower().endswith((".png", ".webp", ".jpg", ".jpeg"))
        and ("icon" in name.lower() or "logo" in name.lower())
    ]
    for candidate in prioritized + fallback:
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _extract_icon(
    apk_path: str, icon_hint: Optional[str]
) -> Tuple[Optional[str], Optional[Any]]:
    if icon_hint and os.path.isfile(icon_hint):
        return os.path.abspath(icon_hint), None

    candidates = _zip_icon_candidates(apk_path, icon_hint)
    if not candidates:
        return None, None

    try:
        with zipfile.ZipFile(apk_path, "r") as archive:
            for member in candidates:
                try:
                    data = archive.read(member)
                except (KeyError, RuntimeError, zipfile.BadZipFile):
                    continue
                if not data:
                    continue
                suffix = Path(member).suffix.lower()
                if suffix not in {".png", ".webp", ".jpg", ".jpeg"}:
                    continue
                temporary_directory = tempfile.TemporaryDirectory(
                    prefix="installatore-apk-"
                )
                output = os.path.join(
                    temporary_directory.name, f"icon{suffix}"
                )
                try:
                    with open(output, "wb") as icon_file:
                        icon_file.write(data)
                except OSError:
                    temporary_directory.cleanup()
                    continue
                return output, temporary_directory
    except (OSError, zipfile.BadZipFile):
        return None, None
    return None, None


def _make_apk_info(apk_path: str, metadata: Dict[str, Any]) -> ApkInfo:
    package = str(metadata.get("package") or "").strip()
    if not package:
        raise ValueError("Il nome del pacchetto non è presente nell’APK.")

    icon_path, temporary_directory = _extract_icon(
        apk_path, metadata.get("icon")
    )

    name = str(metadata.get("name") or "").strip()
    if not name:
        name = package
    version_name = str(metadata.get("version_name") or "—")
    version_code = str(metadata.get("version_code") or "—")
    permissions = [
        str(item) for item in metadata.get("permissions", []) if item
    ]

    return ApkInfo(
        path=apk_path,
        name=name,
        package=package,
        version_name=version_name,
        version_code=version_code,
        permissions=permissions,
        icon_path=icon_path,
        temporary_directory=temporary_directory,
    )


def parse_apk(apk_path: str) -> ApkInfo:
    path = str(Path(apk_path).expanduser().resolve())
    if not os.path.isfile(path):
        raise ValueError(f"File APK non trovato: {apk_path}")

    tool_errors: List[str] = []
    for tool_name in ("aapt2", "aapt"):
        tool = shutil.which(tool_name)
        if tool is None:
            continue
        try:
            result = run_command([tool, "dump", "badging", path], timeout=30)
            if result.returncode != 0:
                detail = AdbClient._format_error(
                    result.stderr or result.stdout
                )
                tool_errors.append(f"{tool_name}: {detail}")
                continue
            metadata = _parse_badging(result.stdout)
            if metadata.get("package"):
                return _make_apk_info(path, metadata)
            tool_errors.append(f"{tool_name}: metadati incompleti")
        except (CommandError, ValueError) as error:
            tool_errors.append(f"{tool_name}: {error}")

    fallback_metadata = _parse_with_pyaxmlparser(path)
    if fallback_metadata is not None:
        try:
            return _make_apk_info(path, fallback_metadata)
        except ValueError as error:
            tool_errors.append(f"pyaxmlparser: {error}")

    details = "\n".join(tool_errors[-3:])
    suffix = f"\n{details}" if details else ""
    raise ValueError(
        "Impossibile leggere i metadati APK. Installa aapt o aapt2, "
        "oppure il pacchetto Python pyaxmlparser." + suffix
    )


def _permission_display_name(permission: str) -> str:
    if permission.startswith(PERMISSION_PREFIX):
        return permission[len(PERMISSION_PREFIX):]
    return permission


class InstallerApplication(_ApplicationBase):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
        )
        self.initial_apk: Optional[str] = None
        self.window: Any = None

    def do_startup(self) -> None:
        _ApplicationBase.do_startup(self)
        self._load_css()

    def do_activate(self) -> None:
        if self.window is None:
            initial_apk = self.initial_apk
            self.initial_apk = None
            self.window = MainWindow(self, initial_apk)
        self.window.present()

    def do_open(self, files: Sequence[Any], n_files: int, hint: str) -> None:
        if not files:
            self.do_activate()
            return
        path = files[0].get_path()
        if not path:
            self.do_activate()
            return
        if self.window is None:
            self.initial_apk = path
            self.do_activate()
            return
        self.window.load_apk(path)
        self.window.present()

    def _load_css(self) -> None:
        css = b"""
        .app-icon-frame {
            border-radius: 18px;
            background: alpha(currentColor, 0.08);
        }
        .app-icon-frame > contents {
            border-radius: 18px;
        }
        .install-button {
            min-height: 44px;
            min-width: 140px;
        }
        .permission-title {
            font-weight: 600;
        }
        .error-label {
            color: #c01c28;
        }
        .busy-label {
            font-weight: 600;
        }
        .download-frame {
            border-radius: 14px;
        }
        .download-frame > contents {
            border-radius: 14px;
            background: alpha(#e66100, 0.14);
        }
        .download-frame.is-pulsing > contents {
            background: alpha(#e66100, 0.30);
        }
        .download-glyph {
            color: #e66100;
        }
        .success-icon-frame {
            background: #26a269;
        }
        .success-icon-frame > contents {
            border-radius: 14px;
        }
        .success-label {
            color: #26a269;
            font-weight: 700;
        }
        """
        try:
            provider = Gtk.CssProvider()
            provider.load_from_data(css)
            display = Gdk.Display.get_default()
            if display is not None:
                Gtk.StyleContext.add_provider_for_display(
                    display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
        except Exception:
            pass


class MainWindow(_ApplicationWindowBase):
    def __init__(
        self, application: Any, initial_apk: Optional[str] = None
    ) -> None:
        super().__init__(application=application)
        self.set_title(APP_TITLE)
        self.set_default_size(620, 780)
        self.set_size_request(360, 560)

        self.adb = AdbClient()
        self.events: queue.Queue = queue.Queue()
        self.devices: List[AdbDevice] = []
        self.current_info: Optional[ApkInfo] = None
        self.current_apk_path: Optional[str] = None
        self.metadata_loading = False
        self.devices_loading = False
        self.installing = False
        self.metadata_token = 0
        self.install_token = 0
        self.adb_error: Optional[str] = None
        self._install_process: Optional[subprocess.Popen] = None
        self._install_process_lock = threading.Lock()
        self._pulse_source_id = 0
        self._file_dialog: Optional[Any] = None
        self._file_chooser: Optional[Any] = None
        self.permission_rows: List[Any] = []

        self._build_ui()
        self._connect_signals()
        GLib.timeout_add(50, self._process_events)
        GLib.idle_add(self._refresh_devices)
        if initial_apk:
            self.load_apk(initial_apk)

    def _build_ui(self) -> None:
        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_vexpand(True)
        self.set_content(self.toast_overlay)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.set_vexpand(True)
        self.toast_overlay.set_child(root)

        header = Adw.HeaderBar()
        self.window_title = Adw.WindowTitle()
        self.window_title.set_title(APP_TITLE)
        self.window_title.set_subtitle("Installazione via ADB")
        header.set_title_widget(self.window_title)

        self.app_header_icon = Gtk.Image()
        _set_app_image(self.app_header_icon)
        self.app_header_icon.set_pixel_size(28)
        self.app_header_icon.set_size_request(28, 28)
        self.app_header_icon.set_valign(Gtk.Align.CENTER)
        self.app_header_icon.set_halign(Gtk.Align.CENTER)
        self.app_header_icon.set_tooltip_text(APP_TITLE)
        header.pack_start(self.app_header_icon)

        self.browse_button = Gtk.Button()
        self.browse_button.set_icon_name("document-open-symbolic")
        self.browse_button.set_tooltip_text("Seleziona un APK")
        header.pack_start(self.browse_button)
        root.append(header)

        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        root.append(self.stack)

        empty_page = Adw.StatusPage()
        empty_page.set_icon_name(APP_ICON_NAME)
        empty_page.set_title("Seleziona un APK")
        empty_page.set_description(
            "Scegli un file APK per leggerne i metadati e installarlo "
            "su un dispositivo Android."
        )
        self.empty_browse_button = Gtk.Button(label="Sfoglia")
        self.empty_browse_button.add_css_class("suggested-action")
        self.empty_browse_button.add_css_class("pill")
        empty_page.set_child(self.empty_browse_button)
        self.stack.add_named(empty_page, "empty")

        content_scroller = Gtk.ScrolledWindow()
        content_scroller.set_policy(
            Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC
        )
        content_scroller.set_vexpand(True)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(20)
        content.set_margin_end(20)
        clamp = Adw.Clamp()
        clamp.set_maximum_size(720)
        clamp.set_child(content)
        content_scroller.set_child(clamp)
        self.stack.add_named(content_scroller, "content")

        self._build_metadata_section(content)
        self._build_device_section(content)
        self._build_permissions_section(content)
        self._build_action_section(content)

    def _build_metadata_section(self, content: Any) -> None:
        header_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=16
        )
        header_box.set_halign(Gtk.Align.START)

        self.icon_frame = Gtk.Frame()
        self.icon_frame.set_size_request(88, 88)
        self.icon_frame.set_halign(Gtk.Align.CENTER)
        self.icon_frame.set_valign(Gtk.Align.CENTER)
        self.icon_frame.add_css_class("app-icon-frame")
        self.app_icon = Gtk.Image()
        _set_app_image(self.app_icon)
        self.app_icon.set_pixel_size(68)
        self.icon_frame.set_child(self.app_icon)
        header_box.append(self.icon_frame)

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        text_box.set_valign(Gtk.Align.CENTER)
        text_box.set_hexpand(True)
        self.app_title = Gtk.Label(label="Seleziona un APK")
        self.app_title.add_css_class("title-1")
        self.app_title.set_wrap(True)
        self.app_title.set_xalign(0)
        self.package_label = Gtk.Label(label="Package: —")
        self.package_label.set_xalign(0)
        self.package_label.set_wrap(True)
        self.package_label.set_selectable(True)
        self.package_label.add_css_class("dim-label")
        self.version_label = Gtk.Label(label="Versione: —")
        self.version_label.set_xalign(0)
        self.version_label.set_wrap(True)
        self.version_label.add_css_class("dim-label")
        self.apk_path_label = Gtk.Label(label="")
        self.apk_path_label.set_xalign(0)
        self.apk_path_label.set_wrap(True)
        self.apk_path_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self.apk_path_label.add_css_class("caption")
        text_box.append(self.app_title)
        text_box.append(self.package_label)
        text_box.append(self.version_label)
        text_box.append(self.apk_path_label)
        header_box.append(text_box)
        content.append(header_box)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        content.append(separator)

    def _build_device_section(self, content: Any) -> None:
        device_group = Adw.PreferencesGroup()
        device_group.set_title("Dispositivo")

        self.device_row = Adw.ActionRow()
        self.device_row.set_title("Dispositivo ADB")
        self.device_row.set_subtitle(
            "Seleziona il dispositivo di destinazione"
        )
        self.device_dropdown = Gtk.DropDown()
        self.device_dropdown.set_hexpand(True)
        self.device_row.add_suffix(self.device_dropdown)

        self.refresh_button = Gtk.Button()
        self.refresh_button.set_icon_name("view-refresh-symbolic")
        self.refresh_button.set_tooltip_text("Ricarica dispositivi")
        self.refresh_button.set_valign(Gtk.Align.CENTER)
        self.device_row.add_suffix(self.refresh_button)
        device_group.add(self.device_row)
        content.append(device_group)

        self.device_status_label = Gtk.Label(label="Ricerca dei dispositivi…")
        self.device_status_label.set_xalign(0)
        self.device_status_label.set_wrap(True)
        self.device_status_label.set_hexpand(True)
        self.device_status_label.add_css_class("dim-label")
        self.device_status_label.set_margin_start(4)

        self.build_label = Gtk.Label(label=_app_version())
        self.build_label.set_valign(Gtk.Align.CENTER)
        self.build_label.add_css_class("dim-label")
        self.build_label.add_css_class("caption")

        status_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=12
        )
        status_row.append(self.device_status_label)
        status_row.append(self.build_label)
        content.append(status_row)

    def _build_permissions_section(self, content: Any) -> None:
        if hasattr(Adw, "ExpanderRow"):
            permissions_group = Adw.PreferencesGroup()
            permissions_group.set_title("Permessi")
            self.permissions_expander = Adw.ExpanderRow()
            self.permissions_expander.set_title("Permessi richiesti")
            self.permissions_expander.set_subtitle(
                "Nessun permesso disponibile"
            )
            permissions_group.add(self.permissions_expander)
            content.append(permissions_group)
            self.permissions_use_adw = True
            return

        self.permissions_use_adw = False
        self.permissions_expander = Gtk.Expander()
        self.permissions_expander.set_label("Permessi richiesti")
        self.permissions_expander.set_expanded(False)
        self.permissions_summary = Gtk.Label(
            label="Nessun permesso disponibile"
        )
        self.permissions_summary.set_xalign(0)
        self.permissions_summary.set_wrap(True)
        self.permissions_summary.add_css_class("dim-label")
        self.permissions_list = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=4
        )
        self.permissions_list.set_margin_top(8)
        permission_content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=4
        )
        permission_content.set_margin_top(8)
        permission_content.set_margin_bottom(8)
        permission_content.set_margin_start(8)
        permission_content.set_margin_end(8)
        permission_content.append(self.permissions_summary)
        permission_content.append(self.permissions_list)
        self.permissions_expander.set_child(permission_content)
        content.append(self.permissions_expander)

    def _build_action_section(self, content: Any) -> None:
        options_group = Adw.PreferencesGroup()
        self.launch_row = Adw.ActionRow()
        self.launch_row.set_title("Opzioni di avvio")
        self.launch_row.set_subtitle(
            "Apre l’applicazione dopo l’installazione"
        )
        self.launch_check = Gtk.CheckButton(label="Avvia al termine")
        self.launch_check.set_valign(Gtk.Align.CENTER)
        self.launch_row.add_suffix(self.launch_check)
        options_group.add(self.launch_row)
        content.append(options_group)

        self.busy_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=10
        )
        self.busy_box.set_halign(Gtk.Align.START)
        self.download_frame = Gtk.Frame()
        self.download_frame.set_size_request(44, 44)
        self.download_frame.set_valign(Gtk.Align.CENTER)
        self.download_frame.add_css_class("download-frame")
        self.download_area = Gtk.Image()
        self.download_area.set_pixel_size(24)
        self.download_area.add_css_class("download-glyph")
        self.download_frame.set_child(self.download_area)
        self._set_download_icon()
        self.busy_label = Gtk.Label(label="Lettura del file APK…")
        self.busy_label.set_wrap(True)
        self.busy_label.add_css_class("busy-label")
        self.cancel_button = Gtk.Button(label="Annulla")
        self.cancel_button.add_css_class("destructive-action")
        self.cancel_button.set_valign(Gtk.Align.CENTER)
        self.busy_box.append(self.download_frame)
        self.busy_box.append(self.busy_label)
        self.busy_box.append(self.cancel_button)
        self.busy_box.set_visible(False)
        content.append(self.busy_box)

        self.error_label = Gtk.Label(label="")
        self.error_label.set_xalign(0)
        self.error_label.set_wrap(True)
        self.error_label.add_css_class("error-label")
        self.error_label.set_visible(False)
        content.append(self.error_label)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        actions.set_halign(Gtk.Align.END)
        self.change_button = Gtk.Button(label="Cambia APK")
        self.change_button.set_valign(Gtk.Align.CENTER)
        self.install_button = Gtk.Button(label="Installa")
        self.install_button.set_icon_name("system-software-install-symbolic")
        self.install_button.add_css_class("suggested-action")
        self.install_button.add_css_class("install-button")
        actions.append(self.change_button)
        actions.append(self.install_button)
        content.append(actions)

        self.success_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=10
        )
        self.success_box.set_halign(Gtk.Align.CENTER)
        self.success_box.set_visible(False)
        self.success_frame = Gtk.Frame()
        self.success_frame.set_size_request(28, 28)
        self.success_frame.set_valign(Gtk.Align.CENTER)
        self.success_frame.add_css_class("success-icon-frame")
        self.success_icon = Gtk.Image()
        self.success_icon.set_from_icon_name("object-select-symbolic")
        self.success_icon.set_pixel_size(18)
        self.success_frame.set_child(self.success_icon)
        self.success_label = Gtk.Label(label="Fatto!")
        self.success_label.set_valign(Gtk.Align.CENTER)
        self.success_label.add_css_class("success-label")
        self.success_box.append(self.success_frame)
        self.success_box.append(self.success_label)
        content.append(self.success_box)

    def _connect_signals(self) -> None:
        self.browse_button.connect(
            "clicked", lambda *_: self._browse_for_apk()
        )
        self.empty_browse_button.connect(
            "clicked", lambda *_: self._browse_for_apk()
        )
        self.change_button.connect(
            "clicked", lambda *_: self._browse_for_apk()
        )
        self.refresh_button.connect(
            "clicked", lambda *_: self._refresh_devices()
        )
        self.device_dropdown.connect(
            "notify::selected", lambda *_: self._update_controls()
        )
        self.install_button.connect(
            "clicked", lambda *_: self._start_install()
        )
        self.cancel_button.connect(
            "clicked", lambda *_: self._cancel_install()
        )
        self.connect("close-request", self._on_close_request)

    def _browse_for_apk(self, *_args: Any) -> None:
        if self.installing:
            return
        if hasattr(Gtk, "FileDialog"):
            self._browse_with_file_dialog()
        else:
            self._browse_with_native_chooser()

    def _browse_with_file_dialog(self) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Seleziona un APK")
        try:
            filters = Gio.ListStore.new(Gtk.FileFilter)
            apk_filter = Gtk.FileFilter()
            apk_filter.set_name("File APK")
            apk_filter.add_pattern("*.apk")
            filters.append(apk_filter)
            dialog.set_filters(filters)
        except (AttributeError, TypeError):
            pass
        self._file_dialog = dialog
        dialog.open(self, None, self._on_file_dialog_open)

    def _on_file_dialog_open(self, dialog: Any, result: Any) -> None:
        try:
            selected_file = dialog.open_finish(result)
        except GLib.Error as error:
            message = getattr(error, "message", "")
            if message and "dismissed" not in message.lower():
                self._show_error("Selezione annullata", message)
            return
        finally:
            self._file_dialog = None
        if selected_file is None:
            return
        path = selected_file.get_path()
        if path:
            self.load_apk(path)

    def _browse_with_native_chooser(self) -> None:
        chooser = Gtk.FileChooserNative(
            title="Seleziona un APK",
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
            accept_label="Apri",
            cancel_label="Annulla",
        )
        self._file_chooser = chooser
        chooser.connect("response", self._on_file_chooser_response)
        chooser.show()

    def _on_file_chooser_response(self, chooser: Any, response: int) -> None:
        if response == Gtk.ResponseType.ACCEPT:
            selected_file = chooser.get_file()
            if selected_file is not None:
                path = selected_file.get_path()
                if path:
                    self.load_apk(path)
        chooser.destroy()
        self._file_chooser = None

    def load_apk(self, path: str) -> None:
        if self.installing:
            return
        if path.startswith("file://"):
            path = Gio.File.new_for_uri(path).get_path() or path
        expanded_path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isfile(expanded_path):
            self._show_error("File non trovato", f"Impossibile aprire: {path}")
            return
        if not expanded_path.lower().endswith(".apk"):
            self._show_error(
                "Formato non valido",
                "Seleziona un file con estensione .apk.",
            )
            return

        self._clear_current_info()
        self.current_apk_path = expanded_path
        self.error_label.set_visible(False)
        self.success_box.set_visible(False)
        self.metadata_token += 1
        token = self.metadata_token
        self.metadata_loading = True
        self._set_metadata_placeholder(expanded_path)
        self.stack.set_visible_child_name("content")
        self._set_busy(True, "Lettura del file APK…")
        self._update_controls()
        threading.Thread(
            target=self._load_apk_worker,
            args=(expanded_path, token),
            daemon=True,
        ).start()

    def _load_apk_worker(self, path: str, token: int) -> None:
        try:
            info = parse_apk(path)
        except Exception as error:
            self.events.put(("apk", token, None, str(error)))
        else:
            self.events.put(("apk", token, info, None))

    def _set_metadata_placeholder(self, path: str) -> None:
        _set_app_image(self.app_icon)
        self.app_icon.set_pixel_size(68)
        self.app_title.set_label("Analisi dell’APK…")
        self.package_label.set_label("Package: —")
        self.version_label.set_label("Versione: —")
        self.apk_path_label.set_label(path)
        self._set_permissions([])

    def _clear_current_info(self) -> None:
        if self.current_info is not None:
            self.current_info.dispose()
        self.current_info = None

    def _refresh_devices(self, *_args: Any) -> bool:
        if self.devices_loading or self.installing:
            return False
        self.devices_loading = True
        self.adb_error = None
        self.device_status_label.set_label("Ricerca dei dispositivi…")
        self._update_controls()
        threading.Thread(
            target=self._discover_devices_worker, daemon=True
        ).start()
        return False

    def _discover_devices_worker(self) -> None:
        try:
            devices = self.adb.discover_devices()
        except Exception as error:
            self.events.put(("devices", None, str(error)))
        else:
            self.events.put(("devices", devices, None))

    def _start_install(self) -> None:
        if (
            self.current_info is None
            or self.metadata_loading
            or self.installing
        ):
            return
        device = self._selected_device()
        if device is None:
            self._show_error(
                "Dispositivo non disponibile",
                "Seleziona un dispositivo ADB autorizzato prima di "
                "installare.",
            )
            return

        self.install_token += 1
        token = self.install_token
        self.installing = True
        self.error_label.set_visible(False)
        self.success_box.set_visible(False)
        self._set_busy(True, f"Installazione su {device.display_name}…")
        self._update_controls()
        apk_info = self.current_info
        launch = self.launch_check.get_active()
        threading.Thread(
            target=self._install_worker,
            args=(token, device, apk_info, launch),
            daemon=True,
        ).start()

    def _install_worker(
        self,
        token: int,
        device: AdbDevice,
        info: ApkInfo,
        launch: bool,
    ) -> None:
        try:
            self.adb.install_apk(
                device,
                info.path,
                lambda line: self.events.put(
                    ("install-output", token, line, None)
                ),
                self._set_install_process,
            )
            launch_message = ""
            if launch:
                try:
                    self.adb.launch_package(device, info.package)
                    launch_message = " Avvio completato."
                except Exception as error:
                    launch_message = (
                        " Installazione completata, ma avvio non riuscito: "
                        f"{error}"
                    )
            self.events.put(
                (
                    "install-done",
                    token,
                    True,
                    "Installazione completata su "
                    f"{device.display_name}.{launch_message}",
                    None,
                )
            )
        except Exception as error:
            self.events.put(("install-done", token, False, str(error), None))

    def _process_events(self) -> bool:
        try:
            while True:
                event = self.events.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        return True

    def _handle_event(self, event: Sequence[Any]) -> None:
        if not event:
            return
        event_type = event[0]
        if event_type == "apk":
            self._handle_apk_event(event)
        elif event_type == "devices":
            self._handle_devices_event(event)
        elif event_type == "install-output":
            _, token, line, _ = event
            if token == self.install_token and self.installing:
                self.busy_label.set_label(self._short_status(line))
        elif event_type == "install-done":
            self._handle_install_done(event)

    def _handle_apk_event(self, event: Sequence[Any]) -> None:
        _, token, info, error = event
        if token != self.metadata_token:
            if info is not None:
                info.dispose()
            return
        self.metadata_loading = False
        if error is not None or info is None:
            self._set_busy(False, "")
            self.app_title.set_label("Impossibile leggere l’APK")
            self._show_error("Analisi APK non riuscita", str(error))
            self._update_controls()
            return
        self.current_info = info
        self.app_icon.set_from_icon_name(
            "application-x-executable-symbolic"
        )
        if info.icon_path:
            self.app_icon.set_from_file(info.icon_path)
        self.app_icon.set_pixel_size(68)
        self.app_title.set_label(f"Installare {info.name}?")
        self.package_label.set_label(f"Package: {info.package}")
        self.version_label.set_label(
            f"Versione: {info.version_name}  ·  Code: {info.version_code}"
        )
        self.apk_path_label.set_label(info.path)
        self._set_permissions(info.permissions)
        self._set_busy(False, "")
        self._update_controls()

    def _handle_devices_event(self, event: Sequence[Any]) -> None:
        _, devices, error = event
        self.devices_loading = False
        if error is not None:
            self.devices = []
            self.adb_error = str(error)
            self._set_device_model(["Nessun dispositivo"])
            self.device_status_label.set_label(str(error))
        else:
            self.devices = devices or []
            self.adb_error = None
            labels = [device.display_name for device in self.devices]
            if not labels:
                labels = ["Nessun dispositivo connesso"]
            self._set_device_model(labels)
            blocked = next(
                (
                    device
                    for device in self.devices
                    if device.state == "no permissions"
                ),
                None,
            )
            if blocked is not None:
                self.device_status_label.set_label(
                    "Accesso USB negato: esegui una volta sola "
                    f"«sudo usermod -aG plugdev {getpass.getuser()}», "
                    "poi esci e rientra nella sessione e ricollega il "
                    "dispositivo. L’app non usa i permessi di "
                    "amministratore."
                )
            elif self.devices:
                ready_index = next(
                    (
                        index
                        for index, device in enumerate(self.devices)
                        if device.is_ready
                    ),
                    0,
                )
                self.device_dropdown.set_selected(ready_index)
                self._update_device_status()
            else:
                self.device_status_label.set_label(
                    "Collega un dispositivo Android e autorizza il debug USB."
                )
        self._update_controls()

    def _set_device_model(self, labels: List[str]) -> None:
        self.device_dropdown.set_model(Gtk.StringList.new(labels))
        if not labels:
            self.device_dropdown.set_selected(0)
        self.device_dropdown.set_sensitive(self.devices_loading is False)

    def _update_device_status(self) -> None:
        device = self._selected_device()
        if device is None:
            if self.devices:
                self.device_status_label.set_label(
                    "Seleziona un dispositivo autorizzato e pronto."
                )
            return
        self.device_status_label.set_label(f"Connesso: {device.display_name}")

    def _selected_device(self) -> Optional[AdbDevice]:
        if not self.devices:
            return None
        index = self.device_dropdown.get_selected()
        if index < 0 or index >= len(self.devices):
            return None
        device = self.devices[index]
        return device if device.is_ready else None

    def _set_permissions(self, permissions: List[str]) -> None:
        if self.permissions_use_adw:
            for row in self.permission_rows:
                self.permissions_expander.remove(row)
        else:
            for row in self.permission_rows:
                self.permissions_list.remove(row)
        self.permission_rows = []

        if self.permissions_use_adw:
            if not permissions:
                self.permissions_expander.set_subtitle(
                    "Nessun permesso richiesto"
                )
                row = Adw.ActionRow()
                row.set_title("Nessun permesso dichiarato")
                self.permissions_expander.add_row(row)
                self.permission_rows.append(row)
                return
            self.permissions_expander.set_subtitle(
                f"{len(permissions)} permessi richiesti"
            )
            for permission in permissions:
                row = Adw.ActionRow()
                row.set_title(_permission_display_name(permission))
                row.set_subtitle(permission)
                row.add_css_class("permission-title")
                self.permissions_expander.add_row(row)
                self.permission_rows.append(row)
            return

        if not permissions:
            self.permissions_summary.set_label("Nessun permesso richiesto")
            row = Adw.ActionRow()
            row.set_title("Nessun permesso dichiarato")
            self.permissions_list.append(row)
            self.permission_rows.append(row)
            return
        self.permissions_summary.set_label(
            f"{len(permissions)} permessi richiesti"
        )
        for permission in permissions:
            row = Adw.ActionRow()
            row.set_title(_permission_display_name(permission))
            row.set_subtitle(permission)
            row.add_css_class("permission-title")
            self.permissions_list.append(row)
            self.permission_rows.append(row)

    def _set_install_process(
        self, process: Optional[subprocess.Popen]
    ) -> None:
        with self._install_process_lock:
            self._install_process = process

    def _cancel_install(self) -> None:
        with self._install_process_lock:
            process = self._install_process
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
            self.busy_label.set_label("Annullamento in corso…")
        except OSError:
            pass

    def _set_download_icon(self) -> None:
        for name in DOWNLOAD_IMAGE_NAMES:
            if _set_image_from_asset(self.download_area, name):
                return
        self._install_causal_drawer()

    def _install_causal_drawer(self) -> None:
        drawer = Gtk.DrawingArea()
        drawer.set_content_width(24)
        drawer.set_content_height(24)
        drawer.set_draw_func(self._draw_download)
        self.download_area = drawer
        self.download_frame.set_child(drawer)

    def _draw_download(
        self, _area: Any, cr: Any, width: int, height: int
    ) -> None:
        size = float(min(width, height))
        if size <= 0:
            return
        cr.set_source_rgb(*DOWNLOAD_COLOR)
        cr.set_line_width(max(2.0, size * 0.1))
        cr.set_line_cap(LINE_CAP_ROUND)
        cr.set_line_join(LINE_JOIN_ROUND)

        left = size * 0.19
        right = size * 0.81
        top = size * 0.46
        bottom = size * 0.86
        radius = size * 0.12
        cr.new_sub_path()
        cr.move_to(left, top)
        cr.line_to(left, bottom - radius)
        cr.arc(
            left + radius,
            bottom - radius,
            radius,
            math.pi,
            1.5 * math.pi,
        )
        cr.line_to(right - radius, bottom)
        cr.arc(
            right - radius,
            bottom - radius,
            radius,
            1.5 * math.pi,
            2 * math.pi,
        )
        cr.line_to(right, top)
        cr.stroke()

        center = size * 0.5
        cr.move_to(center, size * 0.10)
        cr.line_to(center, size * 0.40)
        cr.stroke()
        head = size * 0.17
        cr.move_to(center - head, size * 0.30)
        cr.line_to(center, size * 0.40)
        cr.line_to(center + head, size * 0.30)
        cr.stroke()

    def _toggle_pulse(self) -> bool:
        if not self.busy_box.get_visible():
            self._set_pulse(False)
            return GLib.SOURCE_REMOVE
        if "is-pulsing" in self.download_frame.get_css_classes():
            self.download_frame.remove_css_class("is-pulsing")
        else:
            self.download_frame.add_css_class("is-pulsing")
        return GLib.SOURCE_CONTINUE

    def _set_pulse(self, active: bool) -> None:
        if self._pulse_source_id:
            GLib.source_remove(self._pulse_source_id)
            self._pulse_source_id = 0
        if not active:
            if "is-pulsing" in self.download_frame.get_css_classes():
                self.download_frame.remove_css_class("is-pulsing")
            return
        self._pulse_source_id = GLib.timeout_add(700, self._toggle_pulse)

    def _set_busy(self, visible: bool, message: str) -> None:
        self.busy_box.set_visible(visible)
        self.cancel_button.set_visible(visible and self.installing)
        self._set_pulse(visible)
        if visible:
            self.busy_label.set_label(message)

    def _update_controls(self) -> None:
        device_ready = self._selected_device() is not None
        can_install = (
            self.current_info is not None
            and not self.metadata_loading
            and not self.installing
            and device_ready
        )
        self.install_button.set_sensitive(can_install)
        self.change_button.set_sensitive(not self.installing)
        self.browse_button.set_sensitive(not self.installing)
        self.empty_browse_button.set_sensitive(not self.installing)
        self.device_dropdown.set_sensitive(
            not self.installing
            and not self.devices_loading
            and bool(self.devices)
        )
        self.refresh_button.set_sensitive(
            not self.installing and not self.devices_loading
        )
        self.launch_check.set_sensitive(not self.installing)

        if self.devices_loading:
            return
        if self.adb_error is not None:
            return
        if not self.devices:
            return
        self._update_device_status()

    def _handle_install_done(self, event: Sequence[Any]) -> None:
        _, token, success, message, _ = event
        if token != self.install_token:
            return
        self.installing = False
        self._set_busy(False, "")
        if success:
            self.success_box.set_visible(True)
            self._toast(str(message))
        else:
            self.success_box.set_visible(False)
            self._show_error("Installazione non riuscita", str(message))
        self._update_controls()

    def _short_status(self, text: str) -> str:
        cleaned = " ".join(text.split())
        if len(cleaned) > 100:
            return cleaned[:97] + "…"
        return cleaned

    def _toast(self, message: str) -> None:
        try:
            toast = Adw.Toast.new(message)
            toast.set_timeout(5)
            self.toast_overlay.add_toast(toast)
        except Exception:
            self.device_status_label.set_label(message)

    def _show_error(self, title: str, message: str) -> None:
        self.error_label.set_label(f"{title}: {message}")
        self.error_label.set_visible(True)
        self._toast(f"{title}: {message}")

    def _on_close_request(self, *_args: Any) -> bool:
        self._set_pulse(False)
        with self._install_process_lock:
            process = self._install_process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass
        self._clear_current_info()
        return False


def _find_apk_in_current_directory() -> Optional[str]:
    try:
        entries = sorted(os.listdir("."))
    except OSError:
        return None
    candidates = [
        name for name in entries if name.lower().endswith(".apk")
    ]
    if len(candidates) != 1:
        return None
    return os.path.abspath(candidates[0])


def _parse_arguments(arguments: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="installatore-apk",
        description=APP_TITLE,
        epilog=(
            "Invocato senza percorso usa l'unico file .apk presente "
            "nella cartella corrente."
        ),
    )
    parser.add_argument(
        "apk",
        nargs="?",
        help=(
            "file APK da installare; se omesso viene usato "
            "l'APK nella cartella corrente"
        ),
    )
    values, _unknown = parser.parse_known_args(
        list(arguments) if arguments is not None else None
    )
    return values


def main(arguments: Optional[Sequence[str]] = None) -> int:
    parsed = _parse_arguments(arguments)
    if gi is None or GI_IMPORT_ERROR is not None:
        message = (
            "Impossibile caricare GTK4 o Libadwaita. "
            "Installa python3-gi, gir1.2-gtk-4.0 e gir1.2-adw-1."
        )
        print(message, file=sys.stderr)
        print(f"Dettaglio: {GI_IMPORT_ERROR}", file=sys.stderr)
        return 1

    apk_path = parsed.apk or _find_apk_in_current_directory()
    application = InstallerApplication()
    run_arguments = [sys.argv[0]]
    if apk_path:
        application.initial_apk = apk_path
        run_arguments.append(apk_path)
    return application.run(run_arguments)


if __name__ == "__main__":
    raise SystemExit(main())
