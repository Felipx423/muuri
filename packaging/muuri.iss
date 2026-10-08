#define RepoRoot AddBackslash(SourcePath) + ".."
#define PackageDir RepoRoot + "\..\work\package\dist\Muuri"
[Setup]
AppId={{C02D0CAB-3415-4D1B-AC62-65A50BD751D1}
AppName=Muuri
AppVersion=1.0.2
DefaultDirName={localappdata}\Programs\MuuriDeskPets
DefaultGroupName=Muuri
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#RepoRoot}\..\..\outputs
OutputBaseFilename=Muuri-Setup
SetupIconFile={#RepoRoot}\deskpets\media\muuri\muuri.ico
UninstallDisplayIcon={app}\Muuri.exe
LicenseFile={#RepoRoot}\LICENSE
InfoBeforeFile={#RepoRoot}\packaging\LEIA-ME.txt
Compression=lzma2/ultra64
LZMAUseSeparateProcess=yes
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
CloseApplicationsFilter=Muuri.exe
RestartApplications=no
[InstallDelete]
; Remove DLLs accidentally included by an early test build; use Windows versions.
Type: files; Name: "{app}\_internal\icuuc.dll"
Type: files; Name: "{app}\_internal\icudt78.dll"
Type: files; Name: "{app}\_internal\ucrtbase.dll"
Type: files; Name: "{app}\_internal\api-ms-win-*.dll"
; Remove now-unused optional renderers/codecs from earlier installed versions.
Type: files; Name: "{app}\_internal\PyQt6\Qt6\bin\opengl32sw.dll"
Type: files; Name: "{app}\_internal\PyQt6\Qt6\bin\Qt6Pdf.dll"
Type: files; Name: "{app}\_internal\PyQt6\Qt6\plugins\imageformats\qpdf.dll"
Type: files; Name: "{app}\_internal\PIL\_avif*.pyd"
[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"
[Files]
Source: "{#PackageDir}\*"; DestDir: "{app}"; Excludes: "_internal\deskpets\pets_list.json,_internal\deskpets\config.json,_internal\Muuri-codigo-fonte.zip"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PackageDir}\_internal\deskpets\pets_list.json"; DestDir: "{app}\_internal\deskpets"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "{#PackageDir}\_internal\deskpets\config.json"; DestDir: "{app}\_internal\deskpets"; Flags: onlyifdoesntexist uninsneveruninstall
; Source code is included; assets are provided once under _internal/deskpets/media.
Source: "{#PackageDir}\_internal\Muuri-codigo-fonte.zip"; DestDir: "{app}\_internal"; Flags: ignoreversion
[Icons]
Name: "{group}\Iniciar Muuri"; Filename: "{app}\Muuri.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Iniciar Muuri"; Filename: "{app}\Muuri.exe"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{group}\Desinstalar Muuri"; Filename: "{uninstallexe}"
[Run]
Filename: "{app}\Muuri.exe"; Description: "Abrir Muuri"; Flags: nowait postinstall skipifsilent
