@echo off
::SET apppath=%cd%
::ECHO %apppath%

:: Create ROOT folder in C:\mks
if not exist "C:\mks\" mkdir C:\mks
:: Create temporery folder to extract all needed files.
if not exist "C:\mks\temp\" mkdir C:\mks\temp
:: Create runtime folder to store python.
if not exist "C:\mks\runtime\" mkdir C:\mks\runtime
:: Create applications folder to store installed MakseSense applications.
if not exist "C:\mks\applications\" mkdir C:\mks\applications

:init
setlocal DisableDelayedExpansion
set "batchPath=%~0"
for %%k in (%0) do set batchName=%%~nk
set "vbsGetPrivileges=%temp%\OEgetPriv_%batchName%.vbs"
setlocal EnableDelayedExpansion

:checkPrivileges
NET FILE 1>NUL 2>NUL
if '%errorlevel%' == '0' ( goto gotPrivileges ) else ( goto getPrivileges )

:getPrivileges
if '%1'=='ELEV' (echo ELEV & shift /1 & goto gotPrivileges)
ECHO.
ECHO **************************************
ECHO Invoking UAC for Privilege Escalation
ECHO **************************************

ECHO Set UAC = CreateObject^("Shell.Application"^) > "%vbsGetPrivileges%"
ECHO args = "ELEV " >> "%vbsGetPrivileges%"
ECHO For Each strArg in WScript.Arguments >> "%vbsGetPrivileges%"
ECHO args = args ^& strArg ^& " "  >> "%vbsGetPrivileges%"
ECHO Next >> "%vbsGetPrivileges%"
ECHO UAC.ShellExecute "!batchPath!", args, "", "runas", 1 >> "%vbsGetPrivileges%"
"%SystemRoot%\System32\WScript.exe" "%vbsGetPrivileges%" %*
exit /B

:gotPrivileges
setlocal & pushd .
cd /d %~dp0
if '%1'=='ELEV' (del "%vbsGetPrivileges%" 1>nul 2>nul  &  shift /1)

echo Extract all content of pack.zip to temporery folder.
Call :UnZipFile "C:\mks\temp\" "C:\workspace\Projects\mks_app\mkspack\pack.zip"

echo Extract python into runtime folder.
if not exist "C:\mks\runtime\Python39" Call :UnZipFile "C:\mks\runtime\" "C:\mks\temp\runtime.zip"

echo Remove core folder.
rmdir /S /Q C:\mks\runtime\Python39\Lib\site-packages\core

echo Extract core into Python39\Lib\site-packages folder.
Call :UnZipFile "C:\mks\runtime\Python39\Lib\site-packages\" "C:\mks\temp\core.zip"

echo Extract app into applications folder.
FOR /F %%x in (C:\mks\temp\appname.txt) DO SET appname=%%x
if exist C:\mks\applications\%appname% rmdir /S /Q C:\mks\applications\%appname%
Call :UnZipFile "C:\mks\applications\" "C:\mks\temp\application.zip"

echo Remove links:
rmdir /S /Q C:\mks\applications\%appname%\static\js\core
rmdir /S /Q C:\mks\applications\%appname%\templates

echo Create links
cd C:\mks\applications\%appname%
echo C:\mks\runtime\Python39\python.exe main.py > run.cmd
mklink /D templates C:\mks\runtime\Python39\Lib\site-packages\core\ui\templates
cd C:\mks\applications\%appname%\static\js
mklink /D core C:\mks\runtime\Python39\Lib\site-packages\core\ui\core

echo Remove temp folder.
rmdir /S /Q C:\mks\temp

echo Create shortcat to C:\mks\applications\nasdaq\run.cmd.
Call :MakeShortcat %appname% C:\mks\applications\%appname%

set /p id="Press any key"
exit /b

:UnZipFile <ExtractTo> <newzipfile>
set vbs="%temp%\_.vbs"
if exist %vbs% del /f /q %vbs%
>%vbs%  echo Set fso = CreateObject("Scripting.FileSystemObject")
>>%vbs% echo If NOT fso.FolderExists(%1) Then
>>%vbs% echo fso.CreateFolder(%1)
>>%vbs% echo End If
>>%vbs% echo set objShell = CreateObject("Shell.Application")
>>%vbs% echo set FilesInZip=objShell.NameSpace(%2).items
>>%vbs% echo objShell.NameSpace(%1).CopyHere(FilesInZip)
>>%vbs% echo Set fso = Nothing
>>%vbs% echo Set objShell = Nothing
cscript //nologo %vbs%
if exist %vbs% del /f /q %vbs%
exit /b

:MakeShortcat <shortname> <applicationpath>
set SCRIPT="%TEMP%\%RANDOM%-%RANDOM%-%RANDOM%-%RANDOM%.vbs"

echo Set oWS = WScript.CreateObject("WScript.Shell") >> %SCRIPT%

echo sLinkFile = "%USERPROFILE%\Desktop\%1.lnk" >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
echo oLink.WorkingDirectory = "%2" >> %SCRIPT%
echo oLink.TargetPath = "%2\run.cmd" >> %SCRIPT%
::echo oLink.IconLocation = "\System32\moricons.dll,61" >> %SCRIPT%
echo oLink.Save >> %SCRIPT%

cscript /nologo %SCRIPT%
del %SCRIPT%
exit /b
