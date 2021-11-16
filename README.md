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

# Installation

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

# Usage

## Command-line Options

```text
usage: packetraven [-h] [--callsigns CALLSIGNS] [--aprsfi-key APRSFI_KEY] [--tnc TNC] [--database DATABASE] [--tunnel TUNNEL]
                   [--igate] [--start START] [--end END] [--log LOG] [--output OUTPUT] [--prediction-output PREDICTION_OUTPUT]
                   [--prediction-ascent-rate PREDICTION_ASCENT_RATE] [--prediction-burst-altitude PREDICTION_BURST_ALTITUDE]
                   [--prediction-descent-rate PREDICTION_DESCENT_RATE] [--prediction-float-altitude PREDICTION_FLOAT_ALTITUDE]
                   [--prediction-float-duration PREDICTION_FLOAT_DURATION] [--prediction-api PREDICTION_API] [--interval INTERVAL]
                   [--gui]

optional arguments:
  -h, --help            show this help message and exit
  --callsigns CALLSIGNS
                        comma-separated list of callsigns to track
  --aprsfi-key APRSFI_KEY
                        APRS.fi API key (from https://aprs.fi/page/api)
  --tnc TNC             comma-separated list of serial ports / text files of a TNC parsing APRS packets from analog audio to ASCII
                        (set to `auto` to use the first open serial port)
  --database DATABASE   PostGres database table `user@hostname:port/database/table`
  --tunnel TUNNEL       SSH tunnel `user@hostname:port`
  --igate               send new packets to APRS-IS
  --start START         start date / time, in any common date format
  --end END             end date / time, in any common date format
  --log LOG             path to log file to save log messages
  --output OUTPUT       path to output file to save packets
  --prediction-output PREDICTION_OUTPUT
                        path to output file to save most up-to-date predicted trajectory
  --prediction-ascent-rate PREDICTION_ASCENT_RATE
                        ascent rate to use for prediction (m/s)
  --prediction-burst-altitude PREDICTION_BURST_ALTITUDE
                        burst altitude to use for prediction (m)
  --prediction-descent-rate PREDICTION_DESCENT_RATE
                        descent rate to use for prediction (m/s)
  --prediction-float-altitude PREDICTION_FLOAT_ALTITUDE
                        float altitude to use for prediction (m)
  --prediction-float-duration PREDICTION_FLOAT_DURATION
                        duration of float (s)
  --prediction-api PREDICTION_API
                        API URL to use for prediction (one of ['https://predict.cusf.co.uk/api/v1/',
                        'https://predict.lukerenegar.com/api/v1.1/'])
  --interval INTERVAL   seconds between each main loop (default: 20)
  --gui                 start the graphical interface
```

## Command-line Examples

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

## Graphical User Interface (GUI) Examples

to start the GUI, add `--gui` to any `packetraven` command

```shell
packetraven --gui
```

```shell
packetraven --callsigns W3EAX-8,W3EAX-14 --aprsfi-key <api_key> --gui
```

## Python API Examples

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
