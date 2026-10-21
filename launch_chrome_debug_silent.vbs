' Famous Music Studio - Chrome Remote Debugging Launcher (Silent)
' Bu script Chrome'u remote debugging port 9222 ile sessizce baslatir
' Console penceresi gormez

Set WshShell = CreateObject("WScript.Shell")

CHROME_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"
DEBUG_PORT = 9222
USER_DATA_DIR = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\ChromeDebugProfile"

' Kullanici verisi dizini yoksa olustur
Set fso = CreateObject("Scripting.FileSystemObject")
If Not fso.FolderExists(USER_DATA_DIR) Then
    fso.CreateFolder USER_DATA_DIR
End If

' Chrome zaten acik mi kontrol et (debug portunda)
Set exec = WshShell.Exec("cmd /c netstat -an | findstr :" & DEBUG_PORT)
output = exec.StdOut.ReadAll
If InStr(output, ":" & DEBUG_PORT) > 0 Then
    ' Zaten calisiyor, cik
    WScript.Quit 0
End If

' Chrome debug modunda baslat (pencere gizli)
cmd = CHROME_PATH & " --remote-debugging-port=" & DEBUG_PORT & " --user-data-dir=" & USER_DATA_DIR & " --no-first-run --no-default-browser-check --disable-background-timer-throttling --disable-backgrounding-occluded-windows --disable-renderer-backgrounding"

WshShell.Run cmd, 0, False

' Kisa bekle
WScript.Sleep 3000