"""Locate optional hardware SDKs installed outside the application folder."""

import getpass
import os
from pathlib import Path
import sys


_DLL_HANDLES = []


def _unique_existing_dirs(paths):
    result = []
    seen = set()
    for value in paths:
        if not value:
            continue
        try:
            path = Path(value).expanduser().resolve()
        except Exception:
            continue
        key = str(path).lower()
        if key in seen or not path.is_dir():
            continue
        seen.add(key)
        result.append(path)
    return result


def hardware_path_candidates():
    module_dir = Path(__file__).resolve().parent
    executable_dir = Path(sys.executable).resolve().parent
    current_dir = Path.cwd().resolve()
    user_names = {getpass.getuser(), "user", "14490"}

    paths = []
    env_path = os.environ.get("ART_SCOPE_PYTHON_PATH", "")
    if env_path:
        paths.extend(part for part in env_path.split(os.pathsep) if part)

    for root in (module_dir, executable_dir, current_dir):
        paths.extend(
            (
                root,
                root / "saft_imaging",
                root / "新建文件夹",
                root.parent / "saft_imaging",
                root.parent / "新建文件夹",
                root.parent.parent / "saft_imaging",
                root.parent.parent / "新建文件夹",
            )
        )

    profile = os.environ.get("USERPROFILE")
    if profile:
        paths.append(Path(profile) / "Desktop" / "saft_imaging")
        paths.append(Path(profile) / "Desktop" / "新建文件夹")

    for drive in ("C:", "D:", "E:"):
        for user_name in user_names:
            paths.append(Path(drive + "\\Users") / user_name / "Desktop" / "saft_imaging")
            paths.append(Path(drive + "\\Users") / user_name / "Desktop" / "新建文件夹")
        paths.extend(
            (
                Path(drive + "\\Program Files (x86)")
                / "ART Technology"
                / "ART-SCOPE"
                / "Samples"
                / "Python",
                Path(drive + "\\Program Files")
                / "ART Technology"
                / "ART-SCOPE"
                / "Samples"
                / "Python",
            )
        )
    return _unique_existing_dirs(paths)


def configure_hardware_paths():
    added = []
    for path in hardware_path_candidates():
        value = str(path)
        if value not in sys.path:
            # Hardware helpers are fallbacks. Keeping them after application modules
            # prevents an old fp_lock_pfi_trigger.py from shadowing the bundled one.
            sys.path.append(value)
            added.append(value)

        dll_candidates = (
            path,
            path.parent,
            path.parent.parent,
            path / "bin",
            path / "dll",
            path / "lib",
        )
        for dll_dir in _unique_existing_dirs(dll_candidates):
            dll_value = str(dll_dir)
            if dll_value not in os.environ.get("PATH", "").split(os.pathsep):
                os.environ["PATH"] = dll_value + os.pathsep + os.environ.get("PATH", "")
            if hasattr(os, "add_dll_directory"):
                try:
                    _DLL_HANDLES.append(os.add_dll_directory(dll_value))
                except OSError:
                    pass
    return added


def hardware_import_help(missing_module):
    searched = [str(path) for path in hardware_path_candidates()]
    locations = "\n".join(f"- {path}" for path in searched) or "- 未发现候选目录"
    if missing_module == "art_scope_daq":
        title = "未找到高速采集卡封装 art_scope_daq.py"
        hint = "当前应用已内置该封装；请重新复制完整应用目录。"
    else:
        title = f"未找到高速采集卡SDK模块 {missing_module}"
        hint = "请确认已安装 ART-SCOPE，并保留 Samples\\Python\\ART_SCOPE_Lib。"
    return f"{title}\n{hint}\n已搜索目录:\n{locations}"
