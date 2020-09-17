# PacketRaven 

[![tests](https://github.com/UMDBPP/PacketRaven/workflows/tests/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Atests)
[![build](https://github.com/UMDBPP/PacketRaven/workflows/build/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Abuild)

### Balloon payload telemetry over APRS
PacketRaven is a new version of Link-TLM written in Python

#### Features:
- APRS packet parsing over serial
- log to file
- plotting

#### Installation:
```bash
pip install packetraven
```

###### starting CLI:
```bash
packetraven
```

###### starting GUI:
```bash
packetraven_gui
```

#### In-progress Features
- altitude plot with `matplotlib`
- flight track plot with `cartopy`
- live track prediction
- Iridium telemetry and commands
- live chase navigation
