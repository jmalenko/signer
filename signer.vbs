Set WshShell = CreateObject("WScript.Shell")

scriptDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
exe = scriptDir & ".venv\Scripts\python.exe"

' Build:  "python.exe" main.py ["arg1" "arg2" ...]
cmd = """" & exe & """"
cmd = cmd & " main.py"
For i = 0 To WScript.Arguments.Count - 1
    cmd = cmd & " """ & WScript.Arguments(i) & """"
Next

' Window style 0 = hidden, False = do not wait for python to exit
WshShell.Run cmd, 0, False