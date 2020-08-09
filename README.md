# Huginn 

<a href="https://github.com/UMDBPP/huginn/actions"><img src="https://github.com/UMDBPP/huginn/workflows/tests/badge.svg" /></a>

### Balloon payload telemetry over APRS

Huginn is a new version of Link-TLM written in Python 3.7

Features:
- APRS packet parsing over serial
- log to file
- plotting

#### Installation

##### Running with Python

Make sure you have [Python](https://www.python.org/downloads/) installed with pipenv (`pip install pipenv`), as well as [GitHub Desktop](https://desktop.github.com/) or [command-line Git](https://git-scm.com/download).

1. `git clone https://github.com/UMDBPP/huginn.git`
2. `cd huginn`
3. `pipenv install`
 
##### Building from source

To build a binary executable, you can use PyInstaller (`pipenv install pyinstaller`).

1. `cd huginn`
2. `pyinstaller --paths=C:\Windows\System32\downlevel --onefile huginn_console.py`

#### In-progress features

- altitude plot with `matplotlib`
- flight track plot with `cartopy`
- live track prediction
- Iridium telemetry and commands
- live chase navigation

#### Testing

`python tests.py`
