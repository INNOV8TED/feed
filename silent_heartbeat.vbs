Set WinScriptHost = CreateObject("WScript.Shell")
' Using triple quotes to handle the spaces in "Stephen Portman"
WinScriptHost.Run "python ""C:\Users\Stephen Portman\Desktop\ACTIVE_WORK\activity_feed\heartbeat.py""", 0
Set WinScriptHost = Nothing