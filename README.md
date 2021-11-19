# PacketRaven

[![tests](https://github.com/UMDBPP/PacketRaven/workflows/tests/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Atests)
[![codecov](https://codecov.io/gh/umdbpp/packetraven/branch/master/graph/badge.svg?token=SF5215DHUW)](https://codecov.io/gh/umdbpp/packetraven)
[![build](https://github.com/UMDBPP/PacketRaven/workflows/build/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Abuild)
[![version](https://img.shields.io/pypi/v/packetraven)](https://pypi.org/project/packetraven)
[![license](https://img.shields.io/github/license/umdbpp/packetraven)](https://opensource.org/licenses/MIT)
[![style](https://sourceforge.net/p/oitnb/code/ci/default/tree/_doc/_static/oitnb.svg?format=raw)](https://sourceforge.net/p/oitnb/code)

PacketRaven is a dashboard built to track high-altitude balloon flights from their location telemetry.

```shell
pip install packetraven
```

## installation

0. install Python
   https://www.python.org/downloads/
1. create a virtual environment so you don't pollute your system Python installation (or skip to step 3 if you don't care)
   ```
   pip install virtualenv
   virtualenv packetraven_env
   ```
2. activate your new virtual environment
    - On Linux:
   ```
   source packetraven_env/bin/activate
   ```
    - On Windows native command prompt (`cmd`):
   ```
   .\packetraven_env\Scripts\activate.bat
   ```
    - On Windows PowerShell:
   ```
   .\packetraven_env\Scripts\activate.ps1
   ```
3. install `packetraven`
   ```
   pip install packetraven
   ```

## usage

#### listen to a TNC sending raw APRS strings over USB port COM4

you can set this to `auto` to try the first open USB port

```shell
packetraven --tnc COM4
```

#### listen to APRS.fi, watching specific callsigns

you need an API key to connect to APRS.fi; you can get one from https://aprs.fi/page/api

```shell
packetraven --aprsfi-key <api_key> --callsigns W3EAX-8,W3EAX-14
```

#### listen to a PostGIS database table

```shell
packetraven --database <username>@<hostname>:5432/<database_name>/<table_name>
```

#### watch a text file for new lines containing raw APRS strings

```shell
packetraven --tnc http://bpp.umd.edu/archives/Launches/NS-95_2020-11-07/APRS/W3EAX-11/W3EAX-11_raw_NS95.txt
```

#### listen to a TNC on COM3, watching specific callsigns, and synchronize new packets with a database table via SSH tunnel

```shell
packetraven --tnc COM3 --callsigns W3EAX-8,W3EAX-14 --database <username>@<hostname>:5432/<database_name>/<table_name> --tunnel <ssh_username>@<hostname>:22
```

### graphical user interface (GUI)

to start the GUI, add `--gui` to any `packetraven` command

```shell
packetraven --gui
```

```shell
packetraven --callsigns W3EAX-8,W3EAX-14 --aprsfi-key <api_key> --gui
```

## Python API

to retrieve packets directly from https://aprs.fi:

```python
from packetraven import APRSfi

aprs_fi = APRSfi(
    callsigns=['W3EAX-8', 'W3EAX-12', 'KC3FXX', 'KC3ZRB'],
    api_key='<api_key>',  # enter your APRS.fi API key here - you can get one from https://aprs.fi/page/api
)

print(aprs_fi.packets)
```

or parse packets from a TNC sending parsed APRS over a USB connection:

```python
from packetraven import SerialTNC

tnc = SerialTNC(
    serial_port='COM5',  # set to `'auto'` to connect to the first open serial port
)

print(tnc.packets)
```

or connect to a PostGreSQL database running PostGIS:

```python
from packetraven import APRSDatabaseTable

table = APRSDatabaseTable(
    hostname='<hostname>:5432',
    database='<database_name>',
    table='packets',
    callsigns=['W3EAX-8', 'W3EAX-12', 'KC3FXX', 'KC3ZRB'],
    username='<username>',
    password='<password>',
    ssh_hostname=None,
    ssh_username=None,
    ssh_password=None,
)

print(table.packets)
```
