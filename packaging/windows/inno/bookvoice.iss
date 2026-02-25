#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif

#ifndef SourceDir
  #define SourceDir "..\..\..\dist\windows\pyinstaller\bookvoice"
#endif

#ifndef OutputDir
  #define OutputDir "..\..\..\dist\windows\installer"
#endif

[Setup]
AppId={{F40E74C7-AE52-4C40-B4A6-D17D69DE3D9F}
AppName=Bookvoice
AppVersion={#MyAppVersion}
AppVerName=Bookvoice {#MyAppVersion}
AppPublisher=Bookvoice Contributors
DefaultDirName={localappdata}\Programs\Bookvoice
DefaultGroupName=Bookvoice
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UsePreviousAppDir=yes
UninstallDisplayIcon={app}\bookvoice.exe
OutputDir={#OutputDir}
OutputBaseFilename=bookvoice-windows-x64-v{#MyAppVersion}-setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
LicenseFile={#SourcePath}..\..\..\LICENSE
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourcePath}bookvoice-cli-help.cmd"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Bookvoice CLI"; Filename: "{app}\bookvoice-cli-help.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\bookvoice.exe"
Name: "{group}\Uninstall Bookvoice"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Bookvoice CLI"; Filename: "{app}\bookvoice-cli-help.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\bookvoice.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\bookvoice-cli-help.cmd"; Description: "Open Bookvoice CLI help"; Flags: postinstall nowait skipifsilent
