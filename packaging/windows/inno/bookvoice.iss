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
ChangesEnvironment=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: unchecked
Name: "addtopath"; Description: "Add Bookvoice to the user PATH"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Bookvoice Command Line"; Filename: "{cmd}"; Parameters: "/K cd /d ""{app}"" && .\bookvoice.exe --help"; WorkingDir: "{app}"; IconFilename: "{app}\bookvoice.exe"
Name: "{group}\Uninstall Bookvoice"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Bookvoice Command Line"; Filename: "{cmd}"; Parameters: "/K cd /d ""{app}"" && .\bookvoice.exe --help"; WorkingDir: "{app}"; IconFilename: "{app}\bookvoice.exe"; Tasks: desktopicon

[Run]
Filename: "{cmd}"; Parameters: "/K cd /d ""{app}"" && .\bookvoice.exe --help"; Description: "Open Bookvoice command line"; Flags: postinstall nowait skipifsilent

[Code]
const
  BookvoiceRegistrySubkey = 'Software\Bookvoice';
  UserEnvironmentSubkey = 'Environment';
  PathValueName = 'Path';
  PathMarkerValueName = 'AddedToPath';

function RemoveEnclosingQuotes(const Value: string): string;
begin
  Result := Trim(Value);
  if (Length(Result) >= 2) and (Result[1] = '"') and (Result[Length(Result)] = '"') then
  begin
    Result := Copy(Result, 2, Length(Result) - 2);
  end;
end;

function NormalizePathEntry(const Entry: string): string;
begin
  Result := Uppercase(RemoveEnclosingQuotes(Trim(Entry)));
  while (Length(Result) > 0) and (Result[Length(Result)] = '\') do
  begin
    Delete(Result, Length(Result), 1);
  end;
end;

function PopPathEntry(var PathValue: string): string;
var
  SeparatorIndex: Integer;
begin
  SeparatorIndex := Pos(';', PathValue);
  if SeparatorIndex = 0 then
  begin
    Result := PathValue;
    PathValue := '';
  end
  else
  begin
    Result := Copy(PathValue, 1, SeparatorIndex - 1);
    Delete(PathValue, 1, SeparatorIndex);
  end;
end;

function PathContainsEntry(const PathValue: string; const EntryToFind: string): Boolean;
var
  CandidatePathValue: string;
  CandidateEntry: string;
  NormalizedEntryToFind: string;
begin
  Result := False;
  CandidatePathValue := PathValue;
  NormalizedEntryToFind := NormalizePathEntry(EntryToFind);
  while CandidatePathValue <> '' do
  begin
    CandidateEntry := PopPathEntry(CandidatePathValue);
    if NormalizePathEntry(CandidateEntry) = NormalizedEntryToFind then
    begin
      Result := True;
      Exit;
    end;
  end;
end;

function RemovePathEntry(const PathValue: string; const EntryToRemove: string): string;
var
  CandidatePathValue: string;
  CandidateEntry: string;
  NewPathValue: string;
  NormalizedEntryToRemove: string;
begin
  CandidatePathValue := PathValue;
  NewPathValue := '';
  NormalizedEntryToRemove := NormalizePathEntry(EntryToRemove);

  while CandidatePathValue <> '' do
  begin
    CandidateEntry := Trim(PopPathEntry(CandidatePathValue));
    if (CandidateEntry <> '') and (NormalizePathEntry(CandidateEntry) <> NormalizedEntryToRemove) then
    begin
      if NewPathValue = '' then
      begin
        NewPathValue := CandidateEntry;
      end
      else
      begin
        NewPathValue := NewPathValue + ';' + CandidateEntry;
      end;
    end;
  end;

  Result := NewPathValue;
end;

procedure AddInstallDirectoryToUserPath;
var
  ExistingPath: string;
  InstallDirectory: string;
  UpdatedPath: string;
begin
  InstallDirectory := ExpandConstant('{app}');
  ExistingPath := '';
  RegQueryStringValue(HKCU, UserEnvironmentSubkey, PathValueName, ExistingPath);

  if not PathContainsEntry(ExistingPath, InstallDirectory) then
  begin
    if Trim(ExistingPath) = '' then
    begin
      UpdatedPath := InstallDirectory;
    end
    else
    begin
      UpdatedPath := ExistingPath + ';' + InstallDirectory;
    end;
    RegWriteExpandStringValue(HKCU, UserEnvironmentSubkey, PathValueName, UpdatedPath);
  end;

  RegWriteDWordValue(HKCU, BookvoiceRegistrySubkey, PathMarkerValueName, 1);
end;

procedure RemoveInstallDirectoryFromUserPath;
var
  ExistingPath: string;
  InstallDirectory: string;
  UpdatedPath: string;
begin
  InstallDirectory := ExpandConstant('{app}');
  ExistingPath := '';

  if not RegQueryStringValue(HKCU, UserEnvironmentSubkey, PathValueName, ExistingPath) then
  begin
    Exit;
  end;

  if not PathContainsEntry(ExistingPath, InstallDirectory) then
  begin
    Exit;
  end;

  UpdatedPath := RemovePathEntry(ExistingPath, InstallDirectory);
  if Trim(UpdatedPath) = '' then
  begin
    RegDeleteValue(HKCU, UserEnvironmentSubkey, PathValueName);
  end
  else
  begin
    RegWriteExpandStringValue(HKCU, UserEnvironmentSubkey, PathValueName, UpdatedPath);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('addtopath') then
  begin
    AddInstallDirectoryToUserPath;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AddedToPath: Cardinal;
begin
  if CurUninstallStep <> usUninstall then
  begin
    Exit;
  end;

  AddedToPath := 0;
  if not RegQueryDWordValue(HKCU, BookvoiceRegistrySubkey, PathMarkerValueName, AddedToPath) then
  begin
    Exit;
  end;

  if AddedToPath <> 1 then
  begin
    Exit;
  end;

  RemoveInstallDirectoryFromUserPath;
  RegDeleteValue(HKCU, BookvoiceRegistrySubkey, PathMarkerValueName);
end;
