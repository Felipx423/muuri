"""Fetch official Muuri releases and stage verified platform updates."""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .version import APP_VERSION

REPOSITORY = "Felipx423/muuri"
RELEASES_URL = f"https://github.com/{REPOSITORY}/releases/latest"
LATEST_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
INSTALLER_NAME = "Muuri-Setup.exe"
MACOS_INSTALLER_NAME = "Muuri-macOS-arm64.dmg"
MACOS_CHECKSUM_NAME = "MUURI-macOS-SHA256.txt"
MAX_INSTALLER_BYTES = 200 * 1024 * 1024


@dataclass(frozen=True)
class Release:
    version: str
    tag: str
    installer_url: str
    checksum_url: str
    size: int
    macos_installer_url: str
    macos_checksum_url: str
    macos_size: int


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    url: str
    checksum_url: str
    size: int


def version_tuple(value):
    match = re.fullmatch(r"(?:muuri-v|v)?(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        raise ValueError("Versão de atualização inválida.")
    return tuple(map(int, match.groups()))


def _request(url):
    return Request(url, headers={"User-Agent": f"Muuri/{APP_VERSION}",
                                 "Accept": "application/vnd.github+json" if url == LATEST_API else "application/octet-stream"})


def _check_response(response):
    url = urlsplit(response.geturl())
    if url.scheme != "https" or not (url.hostname in {"github.com", "api.github.com"} or
                                     (url.hostname or "").endswith(".githubusercontent.com")):
        raise ValueError("A atualização não veio de um servidor oficial do GitHub.")


def supported_platform():
    return sys.platform in ("win32", "darwin")


def platform_asset():
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    raise RuntimeError("A atualização não é compatível com esta plataforma.")


def _read_small(url):
    with urlopen(_request(url), timeout=15) as response:
        _check_response(response)
        result = response.read(256 * 1024 + 1)
    if len(result) > 256 * 1024:
        raise ValueError("Resposta de atualização maior que o esperado.")
    return result


def parse_release(data, current=APP_VERSION):
    if data.get("draft") or data.get("prerelease"):
        return None
    tag = data.get("tag_name", "")
    try:
        version = version_tuple(tag)
    except ValueError:
        return None
    if version <= version_tuple(current):
        return None
    assets = {asset["name"]: asset for asset in data.get("assets", [])}
    required = (INSTALLER_NAME, "MUURI-SHA256.txt", MACOS_INSTALLER_NAME, MACOS_CHECKSUM_NAME)
    if any(name not in assets for name in required):
        raise ValueError("A nova versão ainda não tem todos os arquivos para atualizar com segurança.")
    for name in required:
        expected = f"https://github.com/{REPOSITORY}/releases/download/{tag}/{name}"
        if assets[name].get("browser_download_url") != expected:
            raise ValueError("Endereço de atualização diferente do repositório oficial.")
    sizes = {name: assets[name].get("size") for name in (INSTALLER_NAME, MACOS_INSTALLER_NAME)}
    if any(type(size) is not int or not 0 < size <= MAX_INSTALLER_BYTES for size in sizes.values()):
        raise ValueError("Tamanho do instalador inválido.")
    return Release(".".join(map(str, version)), tag,
                   assets[INSTALLER_NAME]["browser_download_url"],
                   assets["MUURI-SHA256.txt"]["browser_download_url"],
                   sizes[INSTALLER_NAME],
                   assets[MACOS_INSTALLER_NAME]["browser_download_url"],
                   assets[MACOS_CHECKSUM_NAME]["browser_download_url"],
                   sizes[MACOS_INSTALLER_NAME])


def check_for_update(current=APP_VERSION):
    return parse_release(json.loads(_read_small(LATEST_API)), current)


def asset_checksum(manifest, name):
    matches = []
    for line in manifest.decode("utf-8-sig").splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?" + re.escape(name), line.strip())
        if match:
            matches.append(match[1].lower())
    if len(matches) != 1:
        raise ValueError(f"Não foi possível confirmar a verificação SHA-256 de {name}.")
    return matches[0]


def installer_checksum(manifest):
    return asset_checksum(manifest, INSTALLER_NAME)


def release_asset(release, platform_name=None):
    platform_name = platform_name or platform_asset()
    if platform_name == "windows":
        return ReleaseAsset(INSTALLER_NAME, release.installer_url, release.checksum_url, release.size)
    if platform_name == "macos":
        return ReleaseAsset(MACOS_INSTALLER_NAME, release.macos_installer_url,
                            release.macos_checksum_url, release.macos_size)
    raise ValueError("Plataforma de atualização inválida.")


def download_update(release, cache, progress=lambda percent: None, cancelled=lambda: False,
                    platform_name=None):
    asset = release_asset(release, platform_name)
    expected = asset_checksum(_read_small(asset.checksum_url), asset.name)
    Path(cache).mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix=f"muuri-{release.version}-", dir=cache))
    partial = folder / f"{asset.name}.part"
    try:
        total, digest = 0, hashlib.sha256()
        with urlopen(_request(asset.url), timeout=15) as response, partial.open("wb") as output:
            _check_response(response)
            while True:
                if cancelled():
                    raise InterruptedError("Atualização cancelada.")
                chunk = response.read(128 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > asset.size or total > MAX_INSTALLER_BYTES:
                    raise ValueError("O instalador recebido tem um tamanho inesperado.")
                output.write(chunk)
                digest.update(chunk)
                progress(min(100, total * 100 // asset.size))
        if total != asset.size or digest.hexdigest() != expected:
            raise ValueError("A verificação do download falhou. Nenhum arquivo do aplicativo foi alterado.")
        downloaded = folder / asset.name
        partial.replace(downloaded)
        return downloaded, expected
    except Exception:
        partial.unlink(missing_ok=True)
        folder.rmdir()
        raise


def can_install_update():
    return (sys.platform == "win32" and bool(getattr(sys, "frozen", False)) and
            Path(sys.executable).name.lower() == "muuri.exe" and
            (Path(sys.executable).parent / "unins000.exe").is_file())


def can_check_for_update():
    return (supported_platform() and bool(getattr(sys, "frozen", False)) and
            Path(sys.executable).exists())


def _ps_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def installer_command(installer, expected, install_dir, parent_pid, target_version=None):
    """Use a Windows helper that outlives Qt and waits for its files to be released."""
    if not re.fullmatch(r"[0-9a-f]{64}", expected) or type(parent_pid) is not int or parent_pid <= 0:
        raise ValueError("Parâmetros de instalação inválidos.")
    installer, install_dir = Path(installer).resolve(), Path(install_dir).resolve()
    if installer.name != INSTALLER_NAME or not installer.is_file():
        raise ValueError("Instalador não encontrado.")
    version_check = ""
    if target_version is not None:
        if not re.fullmatch(r"\d+\.\d+\.\d+", target_version):
            raise ValueError("Versão de instalação inválida.")
        version_check = r"""
    $VersionFile = Join-Path $InstallDir '_internal\deskpets\MUURI-VERSION.txt'
    if (-not (Test-Path -LiteralPath $VersionFile)) { throw 'A instalação não deixou o arquivo de versão disponível.' }
    $InstalledVersion = (Get-Content -LiteralPath $VersionFile -Raw).Trim()
    if ($InstalledVersion -ne $TargetVersion) {
        throw ('A instalação não confirmou a versão ' + $TargetVersion + '.')
    }
"""
    script = r"""
& {
param($InstallerPath, $ExpectedHash, $InstallDir, $ParentProcessId, $TargetVersion)
$ErrorActionPreference = 'Stop'
$LogPath = Join-Path (Split-Path -LiteralPath $InstallerPath) 'update.log'
try {
    $Parent = Get-Process -Id $ParentProcessId -ErrorAction SilentlyContinue
    if ($Parent) { $Parent | Wait-Process -Timeout 120 }
    $Stream = [System.IO.File]::OpenRead($InstallerPath)
    $Hasher = [System.Security.Cryptography.SHA256]::Create()
    try { $ActualHash = [System.BitConverter]::ToString($Hasher.ComputeHash($Stream)).Replace('-', '').ToLowerInvariant() }
    finally { $Stream.Dispose(); $Hasher.Dispose() }
    if ($ActualHash -ne $ExpectedHash) {
        throw 'O instalador foi alterado após o download.'
    }
    $Arguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/SP-', '/NORESTART', '/NOCLOSEAPPLICATIONS',
                   ('/DIR="' + $InstallDir + '"'), ('/LOG="' + $LogPath + '"'))
    $Setup = Start-Process -FilePath $InstallerPath -ArgumentList $Arguments -Wait -PassThru -WindowStyle Hidden
    if ($Setup.ExitCode -ne 0) { throw ('O instalador retornou o código ' + $Setup.ExitCode + '. Consulte ' + $LogPath) }
__VERSION_CHECK__
    Start-Process -FilePath (Join-Path $InstallDir 'Muuri.exe') -WorkingDirectory $InstallDir -WindowStyle Hidden
    Remove-Item -LiteralPath $InstallerPath -Force
} catch {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(('Não foi possível concluir a atualização. ' + $_.Exception.Message), 'Atualização do Muuri') | Out-Null
}
}
"""
    script = script.replace("__VERSION_CHECK__", version_check)
    values = (_ps_literal(installer), _ps_literal(expected), _ps_literal(install_dir),
              str(parent_pid), _ps_literal(target_version or ""))
    script = script.rstrip() + " " + " ".join(values)
    powershell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    return [str(powershell), "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", script]


def launch_installer(installer, expected, target_version=None):
    if not can_install_update():
        raise RuntimeError("A instalação automática está disponível no Muuri instalado no Windows.")
    with Path(installer).open("rb") as source:
        digest = hashlib.sha256()
        for chunk in iter(lambda: source.read(128 * 1024), b""):
            digest.update(chunk)
        if digest.hexdigest() != expected:
            raise ValueError("O instalador foi alterado após o download. Baixe a atualização novamente.")
    command = installer_command(installer, expected, Path(sys.executable).parent, os.getpid(), target_version)
    return subprocess.Popen(command, cwd=Path(installer).parent, close_fds=True,
                            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)


def launch_macos_dmg(image, expected):
    if sys.platform != "darwin":
        raise RuntimeError("A abertura automática do DMG só está disponível no macOS.")
    image = Path(image).resolve()
    if image.name != MACOS_INSTALLER_NAME or not image.is_file():
        raise ValueError("DMG de atualização não encontrado.")
    with image.open("rb") as source:
        digest = hashlib.sha256()
        for chunk in iter(lambda: source.read(128 * 1024), b""):
            digest.update(chunk)
        if digest.hexdigest() != expected:
            raise ValueError("O DMG foi alterado após o download. Baixe a atualização novamente.")
    return subprocess.Popen(["open", str(image)], close_fds=True)
