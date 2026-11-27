@echo off
rem Thin launcher: hands off to the windowless VBScript host and exits.
rem The console flashes briefly; the Signer app itself runs with no console.
rem Usage: signer.bat [-document <file>] [-signature <file>]
wscript.exe "%~dp0signer.vbs" %*
exit /b