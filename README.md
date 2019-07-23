# Huginn 

[![Build Status](https://travis-ci.org/UMDBPP/huginn.svg?branch=master)](https://travis-ci.org/UMDBPP/huginn)

### Balloon payload telemetry over APRS

Huginn is a new version of Link-TLM written in Python 3.7

Features:
- APRS packet parsing over serial
- log to file
- plotting

#### Installation

1. `git clone https://github.com/UMDBPP/huginn.git`
2. `cd huginn`
3. `./dist/huginn.exe serial_port [log_path]`
 
#### Developing

##### Setting up the environment

1. `pip install pipenv`
2. `git clone https://github.com/UMDBPP/huginn.git` 
3. `cd huginn`
4. `pipenv install`

##### Building from source

1. `pip install pyinstaller`
2. `cd huginn`
3. `pyinstaller --paths=C:\Windows\System32\downlevel --onefile huginn_console.py`

#### In-progress features

- altitude plot with `matplotlib`
- flight track plot with `cartopy`
- live track prediction
- Iridium telemetry and commands
- live chase navigation

#### Testing

`python tests/tests/py`
