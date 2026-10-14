#define MyAppName "برنامج الأرشفة"
#define MyAppVersion "1.0.0"
#define MyAppExeName "ArchiveScanner.exe"
#define MyAppPublisher " MOC "
[Setup]
AppId={{7D9E4A12-4E75-4E11-9AF3-0A7C11E2B3D4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Archive
DefaultGroupName=برنامج الأرشفة
OutputBaseFilename=ArchiveScanner-Setup-AR
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin

[Files]
; يُوزَّع ArchiveScanner على شكل مجلد لتفادي فكّ ضغط ملفات Python/Qt/NAPS2
; في كل مرة يشغّل فيها المستخدم التطبيق.
Source: "dist\ArchiveScanner\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\برنامج أرشيف المستندات"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\برنامج أرشيف المستندات"; Filename: "{app}\{#MyAppExeName}"

[Code]
var
  ServerPage: TInputQueryWizardPage;
  DocTypePage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  ServerPage := CreateInputQueryPage(wpSelectDir,
    'إعداد خادم الأرشيف',
    'أدخل عنوان URL لخادم الأرشيف الخاص بمؤسستك',
    'مثال: http://192.168.1.100:8000');
  ServerPage.Add('عنوان URL للخادم:', False);
  ServerPage.Values[0] := 'http://192.168.234.129:8000';

  DocTypePage := CreateInputQueryPage(ServerPage.ID,
    'إعداد نوع المستند',
    'أدخل معرّف نوع المستند الافتراضي في خادم الأرشيف',
    'القيمة الافتراضية هي 4 (اتركها كما هي إذا لم تكن متأكداً).');
  DocTypePage.Add('معرّف نوع المستند:', False);
  DocTypePage.Values[0] := '4';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ServerUrl: String;
  DocType: String;
  DocTypeNumber: Integer;
begin
  Result := True;
  if CurPageID = ServerPage.ID then
  begin
    ServerUrl := Trim(ServerPage.Values[0]);
    if (ServerUrl = '') or ((Pos('http://', Lowercase(ServerUrl)) <> 1) and
       (Pos('https://', Lowercase(ServerUrl)) <> 1)) then
    begin
      MsgBox('يُرجى إدخال عنوان URL صالح يبدأ بـ http:// أو https://', mbError, MB_OK);
      Result := False;
    end;
  end;
  if CurPageID = DocTypePage.ID then
  begin
    DocType := Trim(DocTypePage.Values[0]);
    DocTypeNumber := StrToIntDef(DocType, 0);
    if DocTypeNumber <= 0 then
    begin
      MsgBox('يُرجى إدخال معرّف نوع مستند رقمي موجب.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigFile: String;
  ServerUrl: String;
  DocType: String;
  DocTypeNumber: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    ConfigFile := ExpandConstant('{app}\settings.json');
    ServerUrl := Trim(ServerPage.Values[0]);
    DocType := Trim(DocTypePage.Values[0]);
    DocTypeNumber := StrToIntDef(DocType, 0);
    if DocTypeNumber <= 0 then
      Exit;
    if not SaveStringToFile(ConfigFile,
      '{' + #13#10 +
      '  "server_url": "' + ServerUrl + '",' + #13#10 +
      '  "document_type_id": ' + IntToStr(DocTypeNumber) + #13#10 +
      '}' + #13#10, False) then
      MsgBox('اكتمل التثبيت، لكن تعذّر حفظ إعدادات الخادم.', mbError, MB_OK);
  end;
end;
