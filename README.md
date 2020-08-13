# Huginn 

[![unittests](https://github.com/UMDBPP/huginn/workflows/tests/badge.svg)](https://github.com/UMDBPP/huginn/actions)

### Balloon payload telemetry over APRS
Huginn is a new version of Link-TLM written in Python

#### Features:
- APRS packet parsing over serial
- log to file
- plotting

#### Installation:
```bash
pip install pipenv
git clone https://github.com/UMDBPP/huginn.git
cd huginn
pipenv install
```

#### Starting GUI:
```bash
pipenv run huginn.py
```

#### Building Windows executable:
```cmd
pipenv install pyinstaller
cd huginn
pyinstaller --paths=C:\Windows\System32\downlevel --onefile huginn_console.py
```

#### In-progress Features
- altitude plot with `matplotlib`
- flight track plot with `cartopy`
- live track prediction
- Iridium telemetry and commands
- live chase navigation
