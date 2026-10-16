"""Fetch official Windows releases and stage verified installers outside the app."""
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
MAX_INSTALLER_BYTES = 200 * 1024 * 1024


@dataclass(frozen=True)
class Release:
    version: str
    tag: str
    installer_url: str
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
    if INSTALLER_NAME not in assets or "MUURI-SHA256.txt" not in assets:
        raise ValueError("A nova versão ainda não tem todos os arquivos para atualizar com segurança.")
    for name in (INSTALLER_NAME, "MUURI-SHA256.txt"):
        expected = f"https://github.com/{REPOSITORY}/releases/download/{tag}/{name}"
        if assets[name].get("browser_download_url") != expected:
            raise ValueError("Endereço de atualização diferente do repositório oficial.")
    size = assets[INSTALLER_NAME].get("size")
    if type(size) is not int or not 0 < size <= MAX_INSTALLER_BYTES:
        raise ValueError("Tamanho do instalador inválido.")
    return Release(".".join(map(str, version)), tag, assets[INSTALLER_NAME]["browser_download_url"],
                   assets["MUURI-SHA256.txt"]["browser_download_url"], size)


def check_for_update(current=APP_VERSION):
    return parse_release(json.loads(_read_small(LATEST_API)), current)


def installer_checksum(manifest):
    matches = []
    for line in manifest.decode("utf-8-sig").splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?Muuri-Setup\.exe", line.strip())
        if match:
            matches.append(match[1].lower())
    if len(matches) != 1:
        raise ValueError("Não foi possível confirmar a verificação SHA-256 do instalador.")
    return matches[0]


def download_update(release, cache, progress=lambda percent: None, cancelled=lambda: False):
    expected = installer_checksum(_read_small(release.checksum_url))
    Path(cache).mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix=f"muuri-{release.version}-", dir=cache))
    partial = folder / "download.part"
    try:
        total, digest = 0, hashlib.sha256()
        with urlopen(_request(release.installer_url), timeout=15) as response, partial.open("wb") as output:
            _check_response(response)
            while True:
                if cancelled():
                    raise InterruptedError("Atualização cancelada.")
                chunk = response.read(128 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > release.size or total > MAX_INSTALLER_BYTES:
                    raise ValueError("O instalador recebido tem um tamanho inesperado.")
                output.write(chunk)
                digest.update(chunk)
                progress(min(100, total * 100 // release.size))
        if total != release.size or digest.hexdigest() != expected:
            raise ValueError("A verificação do download falhou. Nenhum arquivo do aplicativo foi alterado.")
        installer = folder / INSTALLER_NAME
        partial.replace(installer)
        return installer, expected
    except Exception:
        partial.unlink(missing_ok=True)
        folder.rmdir()
        raise


def can_install_update():
    return (sys.platform == "win32" and bool(getattr(sys, "frozen", False)) and
            Path(sys.executable).name.lower() == "muuri.exe" and
            (Path(sys.executable).parent / "unins000.exe").is_file())


def _ps_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def installer_command(installer, expected, install_dir, parent_pid):
    """Use a Windows helper that outlives Qt and waits for its files to be released."""
    if not re.fullmatch(r"[0-9a-f]{64}", expected) or type(parent_pid) is not int or parent_pid <= 0:
        raise ValueError("Parâmetros de instalação inválidos.")
    installer, install_dir = Path(installer).resolve(), Path(install_dir).resolve()
    if installer.name != INSTALLER_NAME or not installer.is_file():
        raise ValueError("Instalador não encontrado.")
    script = r"""
& {
param($InstallerPath, $ExpectedHash, $InstallDir, $ParentProcessId)
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
    Start-Process -FilePath (Join-Path $InstallDir 'Muuri.exe') -WorkingDirectory $InstallDir -WindowStyle Hidden
    Remove-Item -LiteralPath $InstallerPath -Force
} catch {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(('Não foi possível concluir a atualização. ' + $_.Exception.Message), 'Atualização do Muuri') | Out-Null
}
}
"""
    script = script.rstrip() + " " + " ".join((_ps_literal(installer), _ps_literal(expected), _ps_literal(install_dir), str(parent_pid)))
    powershell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    return [str(powershell), "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", script]


def launch_installer(installer, expected):
    if not can_install_update():
        raise RuntimeError("A instalação automática está disponível no Muuri instalado no Windows.")
    with Path(installer).open("rb") as source:
        digest = hashlib.sha256()
        for chunk in iter(lambda: source.read(128 * 1024), b""):
            digest.update(chunk)
        if digest.hexdigest() != expected:
            raise ValueError("O instalador foi alterado após o download. Baixe a atualização novamente.")
    command = installer_command(installer, expected, Path(sys.executable).parent, os.getpid())
    return subprocess.Popen(command, cwd=Path(installer).parent, close_fds=True,
                            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
