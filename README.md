# PacketRaven 

[![tests](https://github.com/UMDBPP/PacketRaven/workflows/tests/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Atests)
[![build](https://github.com/UMDBPP/PacketRaven/workflows/build/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Abuild)

PacketRaven is a front-end data aggregator / dashboard, designed to track the progress of high-altitude balloon payload flights via location telemetry.

```bash
pip install packetraven
```

#### Usage:
to start the client, run the following:
```bash
packetraven
```
for usage, do
```bash
packetraven -h
```

there is also a graphical interface:
```bash
packetraven_gui
```

#### Python API:
to retrieve packets directly from https://aprs.fi:
```python
from packetraven import BALLOON_CALLSIGNS, APRS_fi

api_key = '' # enter your APRS.fi API key here - you can get a free API key from https://aprs.fi/page/api

aprs_fi = APRS_fi(BALLOON_CALLSIGNS, api_key)
aprs_fi_packets = aprs_fi.packets

print(aprs_fi_packets)
```
or parse packets from a radio sending parsed APRS over a USB connection:
```python
from packetraven import PacketRadio
 
serial_port = None # leave None to let PacketRaven guess the port name  

radio = PacketRadio(serial_port)
radio_packets = radio.packets

print(radio_packets)
```

#### Features:
###### current:
- parse APRS packets from USB radio
- retrieve packets from https://aprs.fi
- output packets to file
- plot altitude

###### in development:
- flight track plotting
- live track prediction
- Iridium telemetry and commands
- live chase navigation
