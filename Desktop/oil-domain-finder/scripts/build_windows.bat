@echo off
setlocal
py -3.11 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --windowed --name OilDomainFinder main.py
echo.
echo Windows app created at dist\OilDomainFinder\OilDomainFinder.exe
endlocal
