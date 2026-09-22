@echo off
setlocal
set REPO=https://github.com/Vscode5084/forex-trading-engine.git
set WORK=%~dp0fte_repo

REM fresh working copy
if exist "%WORK%" rmdir /s /q "%WORK%"
mkdir "%WORK%"
cd /d "%WORK%"

REM unzip the v1.4.1 package contents into here
powershell -command "Expand-Archive -Path '%~dp0Forex_Trading_Engine_v1.4.1.zip' -DestinationPath '%WORK%' -Force"

REM the zip contains a folder 'smc_engine_pkg' — move its contents to repo root
if exist "%WORK%\smc_engine_pkg" (
  xcopy /e /y /q "%WORK%\smc_engine_pkg\*" "%WORK%\"
  rmdir /s /q "%WORK%\smc_engine_pkg"
)

REM init git + ignore junk (and DON'T commit zips)
git init
git branch -M main
git remote add origin %REPO%
> .gitignore echo __pycache__/
>> .gitignore echo *.pyc
>> .gitignore echo runs/
>> .gitignore echo *.zip

git add -A
git commit -m "v1.4.1 engine (unzipped source)"
REM overwrite the zip-only initial commit
git push -u origin main --force

echo.
echo Done. Username = Vscode5084, password = your ghp_ token.
pause