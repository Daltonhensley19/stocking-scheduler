; Windows installer wizard (Inno Setup 6, https://jrsoftware.org/isinfo.php).
;
; Normally built by `uv run --group build python build.py --installer`, which
; passes AppVersion, SourceDir (the PyInstaller folder build) and OutputDir.
; By hand:  ISCC.exe /DAppVersion=1.0 installer\windows\StockingScheduler.iss

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir SourcePath + "..\..\dist\StockingScheduler"
#endif
#ifndef OutputDir
  #define OutputDir SourcePath + "..\..\release"
#endif

#define AppName "Stocking Scheduler"
#define AppExe "StockingScheduler.exe"

[Setup]
; Never change AppId: it is how Windows recognises a newer version as an
; upgrade of the same program instead of a second copy.
AppId={{6B1E9C42-3A57-4D8E-B0F2-7C9A15E4D3B8}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Stocking 1
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Installs for the current user with no administrator password (store PCs
; usually don't give one out); people with admin rights are offered
; "install for all users" on the first page.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
SetupIconFile={#SourcePath}..\..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
OutputDir={#OutputDir}
; No version in the file name, so the README's "latest download" link never goes stale
OutputBaseFilename=StockingScheduler-Setup-windows
Compression=lzma2/max
SolidCompression=yes
; Offer to close a running copy when upgrading
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
FinishedLabel=Setup has finished installing [name] on your computer. Start it from the Start menu (or the desktop icon, if you chose one).%n%nYour schedules are saved in your own user folder (AppData\Local\StockingScheduler\data). Uninstalling or upgrading never deletes them.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Tells the app it was installed, so it keeps data in the user's folder
Source: "{#SourcePath}installed-by-setup.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
