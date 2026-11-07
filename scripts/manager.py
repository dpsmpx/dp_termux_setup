#!/usr/bin/env python3
"""Interactive, dependency-free setup manager for Termux.

The manager only installs components explicitly selected by the user. It does
not read backup archives, credentials, personal caches, or model repositories.
"""
from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path, PurePosixPath

SCRIPT_PATH = Path(__file__).resolve()
HOME = Path.home()

def _find_repository_root() -> Path | None:
    candidates = (SCRIPT_PATH.parent.parent, SCRIPT_PATH.parent)
    for candidate in candidates:
        if (candidate / ".git").exists() and (candidate / "scripts").is_dir():
            return candidate
    return None

REPOSITORY_ROOT = _find_repository_root()
# A standalone copy remains useful for package management and Android
# toolchain downloads. Repository-only features check REPOSITORY_ROOT first.
ROOT = REPOSITORY_ROOT or SCRIPT_PATH.parent

GROUPS = [
    {
        "title": "Базовые утилиты",
        "description": "Git, SSH, архивы, редакторы и повседневные инструменты.",
        "packages": ["git", "curl", "wget", "openssh", "nano", "vim", "tmux", "htop", "tree", "jq", "rsync", "zip", "unzip", "zstd"],
    },
    {
        "title": "Терминал и shell",
        "description": "Дополнительные оболочки, поиск и интерактивная работа.",
        "packages": ["zsh", "fish", "fzf", "ripgrep", "fd", "zoxide", "starship"],
    },
    {
        "title": "C / C++ development",
        "description": "Компилятор, линкер, CMake, Ninja и инструменты сборки.",
        "packages": ["clang", "lld", "make", "cmake", "ninja", "pkg-config", "binutils", "gdb"],
    },
    {
        "title": "Python",
        "description": "CPython и pip из репозитория Termux.",
        "packages": ["python", "python-pip"],
    },
    {
        "title": "Rust",
        "description": "Rust compiler и Cargo из репозитория Termux.",
        "packages": ["rust"],
    },
    {
        "title": "Node.js",
        "description": "Node.js из репозитория Termux.",
        "packages": ["nodejs"],
    },
    {
        "title": "Java и Gradle",
        "description": "JDK и Gradle для JVM/Android-проектов. Версия выбирается репозиторием Termux.",
        "packages": ["openjdk-21", "gradle"],
    },
    {
        "title": "Android build helpers Termux",
        "description": "ADB/fastboot и системные Android build-компоненты. ndk-sysroot не является полным NDK.",
        "packages": ["android-tools", "ndk-sysroot", "aapt", "apksigner", "ecj"],
    },
    {
        "title": "Python scientific core",
        "description": "NumPy, SciPy и Pillow из репозитория Termux; без Transformers и PyTorch.",
        "packages": ["python-numpy", "python-scipy", "python-pillow"],
    },
    {
        "title": "PyTorch и multimedia",
        "description": "PyTorch, TorchVision, TorchAudio и TorchCodec. Крупная опциональная группа.",
        "packages": ["python-torch", "python-torchvision", "python-torchaudio", "python-torchcodec"],
    },
]

ANDROID_ASSETS = {
    "sdk": {
        "title": "Android SDK ARM64",
        "filename": "android-sdk-aarch64.tar.xz",
        "url": "https://github.com/lzhiyong/termux-ndk/releases/download/android-sdk/android-sdk-aarch64.tar.xz",
        "sha256": "8a23d2a10897ad74e34e10d7d2647ed450fad194d622b8b46e1ebd44557171ad",
        "size": 284690924,
        "target": "android-sdk",
        "check": "sdk",
    },
    "ndk": {
        "title": "Android NDK r29 ARM64",
        "filename": "android-ndk-r29-aarch64.tar.xz",
        "url": "https://github.com/lzhiyong/termux-ndk/releases/download/android-ndk/android-ndk-r29-aarch64.tar.xz",
        "sha256": "02e10e4ddfe8deaeb0bd0cf29d04c981ed5bc8a5d6b560ebb9e7661f472d684b",
        "size": 360538712,
        "target": "android-ndk-r29",
        "check": "ndk",
    },
}

PACKAGE_RE = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")


def clear_screen() -> None:
    if sys.stdout.isatty():
        print("\033[2J\033[H", end="")


def heading(title: str) -> None:
    clear_screen()
    print("=" * 66)
    print(" DP TERMUX SETUP — текстовый менеджер")
    print("=" * 66)
    print(title)
    print("-" * 66)


def pause() -> None:
    input("\nEnter — продолжить...")


def ask_yes_no(question: str, default: bool = False) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    answer = input(f"{question} {suffix} ").strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes", "д", "да"}


def run_command(args: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.STDOUT if capture else None,
            check=False,
        )
    except FileNotFoundError:
        print(f"Команда не найдена: {args[0]}")
        return subprocess.CompletedProcess(args, 127, "", "")


def require_termux() -> bool:
    prefix = os.environ.get("PREFIX", "")
    if not shutil.which("pkg") or not prefix.endswith("/com.termux/files/usr"):
        print("Этот менеджер рассчитан на Termux. Команда pkg или Termux PREFIX не найдены.")
        return False
    return True


def installed_packages() -> set[str]:
    result = run_command(["dpkg-query", "-W", "-f=${db:Status-Abbrev}\\t${binary:Package}\\n"], capture=True)
    if result.returncode != 0:
        return set()
    installed: set[str] = set()
    for line in result.stdout.splitlines():
        fields = line.split("\t", 1)
        if len(fields) == 2 and fields[0].startswith("ii"):
            installed.add(fields[1].strip().split(":", 1)[0])
    return installed


def apt_preview(packages: list[str]) -> bool:
    print("\nПлан APT — только симуляция, система пока не изменяется:\n")
    result = run_command(["apt-get", "install", "--simulate", *packages], capture=True)
    print(result.stdout or "(APT не вернул план)")
    if result.returncode != 0:
        print("Не удалось получить план APT. Обнови списки пакетов и повтори действие.")
        return False
    removals = [line for line in result.stdout.splitlines() if line.startswith("Remv ")]
    if removals:
        print("\nОТМЕНА: план APT собирается удалять пакеты. Менеджер не продолжит такую операцию.")
        return False
    return True


def install_packages(packages: list[str]) -> None:
    packages = list(dict.fromkeys(packages))
    if not packages:
        print("Не выбрано ни одного пакета.")
        return
    invalid = [name for name in packages if not PACKAGE_RE.fullmatch(name)]
    if invalid:
        print("Недопустимые имена пакетов:", ", ".join(invalid))
        return
    current = installed_packages()
    pending = [name for name in packages if name not in current]
    if not pending:
        print("Все выбранные пакеты уже установлены.")
        return
    if not apt_preview(pending):
        return
    print("К установке:", ", ".join(pending))
    if not ask_yes_no("Запустить pkg install?", default=False):
        print("Отменено пользователем.")
        return
    result = run_command(["pkg", "install", *pending])
    if result.returncode == 0:
        print("\nКоманда установки завершилась успешно.")
    else:
        print(f"\nУстановка завершилась с кодом {result.returncode}.")


def package_group_menu() -> None:
    selected: set[int] = set()
    while True:
        heading("Установка пакетных групп")
        current = installed_packages()
        for index, group in enumerate(GROUPS, start=1):
            packages = group["packages"]
            present = sum(1 for package in packages if package in current)
            mark = "[x]" if index - 1 in selected else "[ ]"
            print(f"{index:2}. {mark} {group['title']} ({present}/{len(packages)} уже есть)")
            print(f"    {group['description']}")
        print("\nВведите номер группы для переключения, A — выбрать всё, C — очистить, I — установить, 0 — назад.")
        choice = input("> ").strip().lower()
        if choice == "0":
            return
        if choice == "a":
            selected = set(range(len(GROUPS)))
        elif choice == "c":
            selected.clear()
        elif choice == "i":
            packages: list[str] = []
            for index in sorted(selected):
                packages.extend(GROUPS[index]["packages"])
            install_packages(packages)
            pause()
        elif choice.isdigit() and 1 <= int(choice) <= len(GROUPS):
            index = int(choice) - 1
            if index in selected:
                selected.remove(index)
            else:
                selected.add(index)
        else:
            print("Неизвестный пункт меню.")
            pause()


def package_search_menu() -> None:
    heading("Поиск пакетов Termux")
    query = input("Поисковый запрос: ").strip()
    if not query:
        return
    result = run_command(["pkg", "search", query])
    if result.returncode != 0:
        pause()
        return
    package = input("\nТочное имя пакета для установки (Enter — отмена): ").strip()
    if not package:
        return
    if not PACKAGE_RE.fullmatch(package):
        print("Недопустимое имя пакета.")
        pause()
        return
    install_packages([package])
    pause()


def run_ml_profile() -> None:
    heading("AI / Hugging Face — полный профиль")
    if REPOSITORY_ROOT is None:
        print("Полный AI-профиль доступен в полном клоне репозитория.")
        print("Одна скачанная копия manager.py не содержит локальные DEB/wheel-артефакты и манифесты.")
        pause()
        return
    print("Этот профиль предназначен только для ARM64 и CPython 3.14.")
    print("Он устанавливает локальные Tokenizers/HF Xet DEB, Safetensors/regex wheels,")
    print("а также весь закреплённый pip-набор с Transformers и Hugging Face Hub.")
    print("Это отдельная опция; базовый менеджер не устанавливает AI-пакеты автоматически.")
    print("\nСначала будут проверены SHA-256 всех локальных артефактов.")
    if not ask_yes_no("Открыть установщик полного AI-профиля?", default=False):
        return
    checksum_file = ROOT / "manifests" / "artifact-sha256.txt"
    if not checksum_file.is_file():
        print("Не найден manifests/artifact-sha256.txt")
        pause()
        return
    check = run_command(["sha256sum", "-c", str(checksum_file)])
    if check.returncode != 0:
        print("Проверка артефактов не пройдена. Установка отменена.")
        pause()
        return
    script = ROOT / "scripts" / "install-ml-stack.sh"
    if not script.is_file():
        print("Не найден scripts/install-ml-stack.sh")
    else:
        run_command(["bash", str(script)])
    pause()


def _human_size(value: int) -> str:
    return f"{value / (1024 ** 2):.1f} MiB"


def _download_asset(asset: dict[str, object], cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / str(asset["filename"])
    expected = str(asset["sha256"])
    if target.is_file():
        existing_digest = hashlib.sha256()
        with target.open("rb") as existing:
            for chunk in iter(lambda: existing.read(1024 * 1024), b""):
                existing_digest.update(chunk)
        actual = existing_digest.hexdigest()
        if actual == expected:
            print(f"Уже загружен и проверен: {target.name}")
            return target
        raise RuntimeError(f"Кэш-файл {target.name} имеет неверный SHA-256; он оставлен без изменений.")

    expected_size = int(asset["size"])
    free = shutil.disk_usage(cache_dir).free
    if free < expected_size + 64 * 1024 * 1024:
        raise RuntimeError("Недостаточно места для загрузки архива с временным запасом.")

    partial = target.with_suffix(target.suffix + ".part")
    digest = hashlib.sha256()
    total = 0
    request = urllib.request.Request(
        str(asset["url"]),
        headers={"User-Agent": "dp-termux-setup/0.1", "Accept": "application/octet-stream"},
    )
    print(f"Загрузка {asset['title']} ({_human_size(int(asset['size']))})")
    try:
        with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > expected_size:
                    raise RuntimeError("Сервер передал больше данных, чем заявленный размер архива.")
                output.write(chunk)
                digest.update(chunk)
                print(f"\r  {_human_size(total)} / {_human_size(expected_size)}", end="", flush=True)
        print()
        if total != expected_size:
            raise RuntimeError(f"Размер не совпал: ожидалось {expected_size}, получено {total}.")
        if digest.hexdigest() != expected:
            raise RuntimeError("SHA-256 загруженного файла не совпадает с закреплённым значением.")
        partial.replace(target)
        return target
    except Exception:
        try:
            partial.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _validate_tar_members(archive: tarfile.TarFile, staging: Path) -> tuple[list[tarfile.TarInfo], int]:
    members = archive.getmembers()
    if not members:
        raise RuntimeError("Архив пуст.")
    root = staging.resolve()
    expanded = 0
    for member in members:
        name = PurePosixPath(member.name)
        if name.is_absolute() or ".." in name.parts or "\x00" in member.name:
            raise RuntimeError(f"Небезопасный путь в архиве: {member.name!r}")
        destination = (staging / member.name).resolve(strict=False)
        if destination != root and root not in destination.parents:
            raise RuntimeError(f"Путь выходит за каталог распаковки: {member.name!r}")
        if member.isfile():
            expanded += member.size
        elif member.isdir():
            pass
        elif member.issym():
            if PurePosixPath(member.linkname).is_absolute():
                raise RuntimeError(f"Абсолютная символическая ссылка: {member.name!r}")
            target = (destination.parent / member.linkname).resolve(strict=False)
            if target != root and root not in target.parents:
                raise RuntimeError(f"Символическая ссылка выходит за каталог распаковки: {member.name!r}")
        elif member.islnk():
            link = PurePosixPath(member.linkname)
            if link.is_absolute() or ".." in link.parts:
                raise RuntimeError(f"Небезопасная hard link: {member.name!r}")
        else:
            raise RuntimeError(f"Специальный тип файла в архиве запрещён: {member.name!r}")
    return members, expanded


def _locate_payload(staging: Path, asset: dict[str, object]) -> Path:
    expected = str(asset["target"])
    preferred = staging / expected
    candidates = [preferred] if preferred.is_dir() else [p for p in staging.iterdir() if p.is_dir()]
    if not candidates and str(asset["check"]) == "sdk":
        candidates = [staging]
    if len(candidates) != 1:
        raise RuntimeError("Не удалось однозначно определить корневой каталог Android-архива.")
    candidate = candidates[0]
    check = str(asset["check"])
    if check == "sdk":
        has_platform_tools = (candidate / "platform-tools" / "adb").is_file()
        has_build_tools = (candidate / "build-tools").is_dir()
        if not (has_platform_tools and has_build_tools):
            raise RuntimeError("В SDK-архиве не обнаружены platform-tools/adb и build-tools.")
    else:
        clang = candidate / "toolchains" / "llvm" / "prebuilt" / "linux-aarch64" / "bin" / "clang"
        if not clang.is_file():
            raise RuntimeError("В NDK-архиве не обнаружен ARM64 LLVM clang.")
    return candidate


def _extract_asset(archive_path: Path, asset: dict[str, object], install_root: Path) -> Path:
    final = install_root / str(asset["target"])
    if final.exists():
        raise RuntimeError(f"Целевой каталог уже существует; он не будет перезаписан: {final}")

    staging = Path(tempfile.mkdtemp(prefix=".dp-termux-setup-", dir=install_root))
    try:
        with tarfile.open(archive_path, mode="r:xz") as archive:
            members, expanded = _validate_tar_members(archive, staging)
            free = shutil.disk_usage(install_root).free
            required = expanded + 128 * 1024 * 1024
            print(f"Размер распаковки: {_human_size(expanded)}; свободно: {_human_size(free)}")
            if free < required:
                raise RuntimeError("Недостаточно свободного места для безопасной распаковки.")
            if hasattr(tarfile, "data_filter"):
                archive.extractall(path=staging, members=members, filter="data")
            else:
                archive.extractall(path=staging, members=members)
        payload = _locate_payload(staging, asset)
        if payload == staging:
            raise RuntimeError("Архив распакован без отдельного корневого каталога; автоматическая установка остановлена.")
        shutil.move(str(payload), str(final))
        print(f"Установлено: {final}")
        return final
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _write_android_env(paths: dict[str, Path]) -> None:
    import shlex

    config_dir = HOME / ".config" / "dp-termux-setup"
    env_file = config_dir / "android-env.sh"
    if env_file.exists():
        print(f"Файл уже существует и не будет перезаписан: {env_file}")
        return
    lines = ["# Android toolchain paths generated by dp-termux-setup."]
    for key, path in paths.items():
        # shlex.quote prevents shell expansion even if a custom path contains
        # spaces, quotes, dollar signs or command-substitution characters.
        lines.append(f"export {key}={shlex.quote(str(path.resolve()))}")
    if "ANDROID_HOME" in paths:
        lines.append('export ANDROID_SDK_ROOT="$ANDROID_HOME"')
    config_dir.mkdir(parents=True, exist_ok=True)
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Создан локальный файл окружения: {env_file}")
    print(f'Для текущей сессии: source "{env_file}"')
    print("Автоматически менять .bashrc/.zshrc менеджер не будет.")


def android_install_menu() -> None:
    heading("Android SDK / NDK — ARM64 toolchains")
    print("Источником выбранных архивов является community-проект lzhiyong/termux-ndk,")
    print("а не официальный бинарный дистрибутив Google. Версии и SHA-256 закреплены в менеджере.")
    print("SDK: build-tools 35.0.0 и platform-tools 35.0.2 (состав релиза может быть ограничен).")
    print("NDK: r29, сборка для Linux AArch64/Termux.")
    print("Архивы загружаются отдельно по выбору; существующие каталоги никогда не перезаписываются.\n")
    if platform.machine().lower() not in {"aarch64", "arm64"}:
        print("Эта сборка SDK/NDK рассчитана только на ARM64.")
        pause()
        return
    api_result = run_command(["getprop", "ro.build.version.sdk"], capture=True)
    if api_result.returncode == 0 and api_result.stdout.strip().isdigit():
        android_api = int(api_result.stdout.strip())
        if android_api < 28:
            print(f"Обнаружен Android API {android_api}; upstream archive requires Android 9 / API 28 or newer.")
            pause()
            return
    print("1. Только Android SDK (около 272 MiB)")
    print("2. Только Android NDK r29 (около 344 MiB)")
    print("3. SDK + NDK (около 616 MiB загрузки)")
    print("0. Назад")
    choice = input("> ").strip()
    if choice == "0":
        return
    if choice not in {"1", "2", "3"}:
        return
    selected = ["sdk"] if choice == "1" else ["ndk"] if choice == "2" else ["sdk", "ndk"]
    default_root = HOME / "opt"
    raw_root = input(f"Каталог установки [{default_root}]: ").strip()
    install_root = Path(raw_root).expanduser() if raw_root else default_root
    try:
        install_root = install_root.resolve()
        if install_root == ROOT or ROOT in install_root.parents:
            raise RuntimeError("Нельзя устанавливать Android toolchain внутрь каталога репозитория.")
        install_root.mkdir(parents=True, exist_ok=True)
        for key in selected:
            target = install_root / str(ANDROID_ASSETS[key]["target"])
            if target.exists():
                raise RuntimeError(f"Целевой каталог уже существует; он не будет изменён: {target}")
    except Exception as exc:
        print(f"Ошибка каталога установки: {exc}")
        pause()
        return

    if not ask_yes_no("Продолжить загрузку и проверку архивов?", default=False):
        return
    cache_dir = HOME / ".cache" / "dp-termux-setup" / "downloads"
    installed: dict[str, Path] = {}
    for key in selected:
        asset = ANDROID_ASSETS[key]
        try:
            archive_path = _download_asset(asset, cache_dir)
            installed[key] = _extract_asset(archive_path, asset, install_root)
        except Exception as exc:
            print(f"\nНе удалось установить {asset['title']}: {exc}")
            print("Уже существующие каталоги и проверенные архивы оставлены без изменения.")
            break

    if installed:
        env_paths: dict[str, Path] = {}
        if "sdk" in installed:
            env_paths["ANDROID_HOME"] = installed["sdk"]
        if "ndk" in installed:
            env_paths["ANDROID_NDK_HOME"] = installed["ndk"]
        print("\nУстановленные компоненты:")
        for key, path in installed.items():
            print(f"  {ANDROID_ASSETS[key]['title']}: {path}")
        if ask_yes_no("Создать отдельный локальный файл переменных окружения?", default=True):
            _write_android_env(env_paths)
        else:
            for key, path in env_paths.items():
                print(f"export {key}='{path}'")
            if "ANDROID_HOME" in env_paths:
                print('export ANDROID_SDK_ROOT="$ANDROID_HOME"')
    pause()


def _find_android_paths() -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []
    for variable, label in (("ANDROID_HOME", "ANDROID_HOME"), ("ANDROID_SDK_ROOT", "ANDROID_SDK_ROOT"), ("ANDROID_NDK_HOME", "ANDROID_NDK_HOME"), ("ANDROID_NDK_ROOT", "ANDROID_NDK_ROOT")):
        value = os.environ.get(variable)
        if value:
            path = Path(value).expanduser()
            if path.exists():
                candidates.append((label, path))
    for path in (
        HOME / "opt" / "android-sdk",
        HOME / "opt" / "android-ndk-r29",
        HOME / "android" / "android-sdk",
        HOME / "android" / "android-ndk-r29",
        HOME / "android" / "ndk",
    ):
        if path.exists():
            candidates.append(("Найден каталог", path))
    return candidates


def environment_status() -> None:
    heading("Состояние Termux")
    print(f"Архитектура: {platform.machine()}")
    print(f"Python: {platform.python_version()}")
    print(f"PREFIX задан: {'да' if os.environ.get('PREFIX') else 'нет'}")
    print(f"pkg: {shutil.which('pkg') or 'не найден'}")
    print(f"Свободное место в HOME: {_human_size(shutil.disk_usage(HOME).free)}")
    print("\nУстановленные группы (по dpkg):")
    current = installed_packages()
    for group in GROUPS:
        count = sum(1 for name in group["packages"] if name in current)
        if count:
            print(f"  {group['title']}: {count}/{len(group['packages'])}")
    print("\nAndroid SDK/NDK:")
    found = _find_android_paths()
    if found:
        for label, path in found:
            print(f"  {label}: {path}")
    else:
        print("  известные каталоги и переменные окружения не найдены")
    pause()


def update_menu() -> None:
    heading("Обновление Termux")
    print("1. pkg update — обновить списки пакетов")
    print("2. pkg upgrade — обновить установленные пакеты")
    print("0. Назад")
    choice = input("> ").strip()
    if choice == "1":
        if ask_yes_no("Выполнить pkg update?", default=False):
            run_command(["pkg", "update"])
    elif choice == "2":
        print("Обновление может затронуть весь набор установленных пакетов.")
        if ask_yes_no("Выполнить pkg upgrade?", default=False):
            run_command(["pkg", "upgrade"])
    pause()


def storage_setup() -> None:
    heading("Доступ к общей памяти Android")
    print("Будет вызвана штатная команда Termux termux-setup-storage.")
    print("Она запросит разрешение Android и создаст ссылки в ~/storage.")
    if ask_yes_no("Продолжить?", default=False):
        run_command(["termux-setup-storage"])
    pause()


def privacy_audit() -> None:
    heading("Проверка приватности репозитория")
    if REPOSITORY_ROOT is None:
        print("Аудит доступен только из полного клона репозитория.")
        pause()
        return
    script = ROOT / "scripts" / "privacy_audit.py"
    if not script.is_file():
        print("Не найден scripts/privacy_audit.py")
    else:
        run_command([sys.executable, str(script), "--root", str(ROOT)])
    pause()



def preview_package_groups() -> None:
    """Interactive simulation of group selection with no system side effects."""
    selected: set[int] = set()
    while True:
        heading("Предпросмотр — выбор пакетных групп")
        print("Демонстрация выбора. Ни одна команда установки не выполняется.\n")
        for index, group in enumerate(GROUPS, start=1):
            mark = "[x]" if index - 1 in selected else "[ ]"
            print(f"{index:2}. {mark} {group['title']}")
            print(f"    {group['description']}")
            print(f"    Пакеты: {', '.join(group['packages'])}")
        print("\nНомер — переключить группу, A — выбрать всё, C — очистить, I — показать итог, 0 — назад.")
        choice = input("> ").strip().lower()
        if choice == "0":
            return
        if choice == "a":
            selected = set(range(len(GROUPS)))
        elif choice == "c":
            selected.clear()
        elif choice == "i":
            packages: list[str] = []
            for index in sorted(selected):
                packages.extend(GROUPS[index]["packages"])
            heading("Предпросмотр — выбранные пакеты")
            if packages:
                print(f"Выбрано групп: {len(selected)}")
                print(f"Уникальных пакетов: {len(set(packages))}\n")
                for package in dict.fromkeys(packages):
                    print(f"  • {package}")
            else:
                print("Пакетные группы не выбраны.")
            print("\nЭто демонстрация. APT не вызывается, установка не запускается.")
            pause()
        elif choice.isdigit() and 1 <= int(choice) <= len(GROUPS):
            index = int(choice) - 1
            if index in selected:
                selected.remove(index)
            else:
                selected.add(index)
        else:
            print("Неизвестный пункт меню.")
            pause()


def preview_mode() -> int:
    """Read-only UI preview; safe to run from a single downloaded file."""
    while True:
        heading("Предпросмотр интерфейса — режим только чтения")
        print("Демонстрационный режим: команды установки и загрузки отключены.\n")
        print("1. Установка пакетных групп")
        print("2. Поиск и установка отдельного пакета")
        print("3. Полный AI / Hugging Face профиль")
        print("4. Android SDK / NDK ARM64")
        print("5. Обновление списков / пакетов")
        print("6. Настройка доступа к общей памяти")
        print("7. Состояние окружения")
        print("8. Аудит приватности репозитория")
        print("0. Выход")
        choice = input("\nВыбор: ").strip()
        if choice == "0":
            return 0
        if choice == "1":
            preview_package_groups()
        elif choice == "2":
            heading("Предпросмотр — поиск пакета")
            print("В рабочем режиме менеджер вызывает pkg search, затем просит точное имя пакета.")
            print("Перед установкой отображается симуляция APT.\n")
            pause()
        elif choice == "3":
            heading("Предпросмотр — AI / Hugging Face")
            print("Отдельный профиль: Tokenizers, HF Xet, Safetensors, regex, Transformers и Hub.")
            print("Будут проверены SHA-256 локальных артефактов до установки.\n")
            pause()
        elif choice == "4":
            heading("Предпросмотр — Android SDK / NDK")
            print("1. Только Android SDK ARM64")
            print("2. Только Android NDK r29 ARM64")
            print("3. SDK + NDK")
            print("0. Назад")
            print("\nПеред загрузкой показываются размеры и запрашивается подтверждение.")
            pause()
        elif choice == "5":
            heading("Предпросмотр — обновление Termux")
            print("1. pkg update")
            print("2. pkg upgrade")
            print("0. Назад")
            print("\nОбе операции запускаются только после отдельного подтверждения.")
            pause()
        elif choice == "6":
            heading("Предпросмотр — общая память Android")
            print("Штатная команда termux-setup-storage; Android отдельно запросит разрешение.")
            pause()
        elif choice == "7":
            heading("Предпросмотр — состояние окружения")
            print("Показываются архитектура, версия Python, свободное место, группы пакетов и найденные SDK/NDK.")
            pause()
        elif choice == "8":
            heading("Предпросмотр — аудит приватности")
            print("Проверка исходников, локальных путей, токенов, ключей и метаданных Git-коммитов.")
            print("При запуске из отдельного файла сканирование домашнего каталога не выполняется.")
            pause()
        else:
            print("Неизвестный пункт меню.")
            pause()


def main() -> int:
    if not require_termux():
        return 2
    while True:
        heading("Главное меню")
        print("1. Установка пакетных групп")
        print("2. Поиск и установка отдельного пакета")
        print("3. Полный AI / Hugging Face профиль")
        print("4. Android SDK / NDK ARM64")
        print("5. Обновление списков / пакетов")
        print("6. Настройка доступа к общей памяти")
        print("7. Состояние окружения")
        print("8. Аудит приватности репозитория")
        print("0. Выход")
        choice = input("\nВыбор: ").strip()
        if choice == "0":
            return 0
        if choice == "1":
            package_group_menu()
        elif choice == "2":
            package_search_menu()
        elif choice == "3":
            run_ml_profile()
        elif choice == "4":
            android_install_menu()
        elif choice == "5":
            update_menu()
        elif choice == "6":
            storage_setup()
        elif choice == "7":
            environment_status()
        elif choice == "8":
            privacy_audit()
        else:
            print("Неизвестный пункт меню.")
            pause()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DP Termux Setup — текстовый менеджер")
    parser.add_argument("--preview", action="store_true", help="показать интерфейс без выполнения системных команд")
    args = parser.parse_args()
    try:
        raise SystemExit(preview_mode() if args.preview else main())
    except KeyboardInterrupt:
        print("\nПрервано пользователем.")
        raise SystemExit(130)
