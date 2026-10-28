@echo off
cd /d "%~dp0"
if not exist install_mod.exe (
  echo install_mod.exe not found. Unpack TWFC-AllCharacters.zip from the release into the game folder.
  pause
  exit /b 1
)
install_mod.exe --fps-unlimited
pause
