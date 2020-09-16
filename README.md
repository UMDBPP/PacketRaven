# Huginn 

[![tests](https://github.com/UMDBPP/huginn/workflows/tests/badge.svg)](https://github.com/UMDBPP/huginn/actions?query=workflow%3Atests)
[![build](https://github.com/UMDBPP/huginn/workflows/build/badge.svg)](https://github.com/UMDBPP/huginn/actions?query=workflow%3Abuild)

### Balloon payload telemetry over APRS
Huginn is a new version of Link-TLM written in Python

#### Features:
- APRS packet parsing over serial
- log to file
- plotting

#### Installation:
```bash
pip install huginn
```

#### Starting GUI:
```bash
huginn
```

#### Starting CLI:
```bash
huginn_cli
```

#### In-progress Features
- altitude plot with `matplotlib`
- flight track plot with `cartopy`
- live track prediction
- Iridium telemetry and commands
- live chase navigation
