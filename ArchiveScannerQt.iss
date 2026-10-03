#define MyAppName "Archive Scanner"
#define MyAppVersion "1.0.0"
#define MyAppExeName "ArchiveScanner.exe"
#define MyAppPublisher " MOC "
[Setup]
AppId={{7D9E4A12-4E75-4E11-9AF3-ARCHIVESCANNER}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Archive
DefaultGroupName=Archive Scanner
OutputBaseFilename=ArchiveScanner-Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin

[Files]
; ArchiveScanner is built as a folder distribution. This avoids unpacking
; the Python/Qt/NAPS2 files every time the user opens the application.
Source: "dist\ArchiveScanner\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\DocArchive Scanner"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\DocArchive Scanner"; Filename: "{app}\{#MyAppExeName}"

[Code]
var
  ServerPage: TInputQueryWizardPage;
  DocTypePage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  ServerPage := CreateInputQueryPage(wpSelectDir,
    'Archive Server Configuration',
    'Enter the Mayan EDMS server URL for your organization',
    'Example: http://192.168.1.100:8000');
  ServerPage.Add('Server URL:', False);
  ServerPage.Values[0] := 'http://192.168.234.129:8000';

  DocTypePage := CreateInputQueryPage(ServerPage.ID,
    'Document Type Configuration',
    'Enter the default Mayan EDMS Document Type ID',
    'Default is 4 (leave as is if unsure).');
  DocTypePage.Add('Document Type ID:', False);
  DocTypePage.Values[0] := '4';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ConfigFile: String;
  ServerUrl: String;
  DocType: String;
begin
  Result := True;
  if CurPageID = ServerPage.ID then
  begin
    ServerUrl := Trim(ServerPage.Values[0]);
    if (ServerUrl = '') or ((Pos('http://', Lowercase(ServerUrl)) <> 1) and
       (Pos('https://', Lowercase(ServerUrl)) <> 1)) then
    begin
      MsgBox('Please enter a valid URL starting with http:// or https://', mbError, MB_OK);
      Result := False;
    end;
  end;
  if CurPageID = DocTypePage.ID then
  begin
    DocType := Trim(DocTypePage.Values[0]);
    if DocType = '' then
    begin
      MsgBox('Please enter a valid Document Type ID.', mbError, MB_OK);
      Result := False;
    end;
  end;
  if Result and (CurPageID = wpReady) then
  begin
    ConfigFile := ExpandConstant('{app}\settings.json');
    ServerUrl := Trim(ServerPage.Values[0]);
    DocType := Trim(DocTypePage.Values[0]);
    SaveStringToFile(ConfigFile,
      '{' + #13#10 +
      '  "server_url": "' + ServerUrl + '",' + #13#10 +
      '  "document_type_id": ' + DocType + #13#10 +
      '}' + #13#10, False);
  end;
end;
