@echo off
setlocal
py -3.11 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --windowed --collect-submodules sources --name CompanyDomainFinder main.py
echo.
echo Windows app created at dist\CompanyDomainFinder\CompanyDomainFinder.exe
echo To make the one-click installer, install Inno Setup and compile installer\CompanyDomainFinder.iss.
endlocal
