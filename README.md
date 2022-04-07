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

## Installation

1. install Python - https://www.python.org/downloads/

2. install `packetraven` with `pip`:
    ```
    pip install packetraven
    ```

---
**NOTE**

Alternatively, you may download the source code and build from source:

```shell
git clone https://github.com/UMDBPP/PacketRaven.git
cd packetraven
pip install .
```

---

## Usage

PacketRaven reads a configuration file to determine which connections to set up, how to parse your packets, which callsigns to filter, etc.

```bash
packetraven /path/to/config.yaml
```

The configuration is in YAML format. Here is an example configuration:

```yaml
# config.yaml

callsigns:
    - W3EAX-9
    - W3EAX-11
    - W3EAX-12

time:
    start: 2022-03-05
    end: 2022-03-06
    interval: 30

output:
    filename: ns110.geojson

log:
    filename: ns110.log

packets:
    aprs_fi:
        api_key: 123456.abcdefhijklmnop
    text:
        locations:
            - /dev/ttyUSB0
            - ~/packets.txt
    database:
        hostname: localhost
        port: 5432
        database: nearspace
        table: ns110
        username: user1
        password: password1
        tunnel:
            hostname: bpp.umd.edu
            port: 22
            username: user1
            password: password2

prediction:
    start:
        location:
            - -78.4987
            - 40.0157
        time: 2022-03-05 10:36:00
    profile:
        ascent_rate: 6.5
        burst_altitude: 25000
        sea_level_descent_rate: 9
    output:
        filename: ns110_prediction.geojson
```

### start the graphical user interface (GUI)

to start the GUI, add `--gui` to any `packetraven` command

```shell
packetraven --gui
packetraven config.yaml --gui
```

## Examples

#### listen to a TNC sending raw APRS strings over USB port COM4

```yaml
# config.yaml

packets:
    text:
        locations:
            - COM4
```

you can also set the location to `auto` to try the first open USB port

```yaml
# config.yaml

packets:
    text:
        locations:
            - auto
```

#### listen to APRS.fi, watching specific callsigns

you need an API key to connect to APRS.fi; you can get one from https://aprs.fi/page/api

```yaml
# config.yaml

callsigns:
    - W3EAX-8
    - W3EAX-14

packets:
    aprs_fi:
        api_key: 123456.abcdefhijklmnop
```

#### listen to a PostGIS database table

```yaml
# config.yaml

callsigns:
    - W3EAX-8
    - W3EAX-14

packets:
    database:
        hostname: bpp.umd.edu
        port: 5432
        database: nearspace
        table: ns110
        username: user1
        password: password1
```

#### watch text file(s) for new lines containing raw APRS strings

```yaml
# config.yaml

packets:
    text:
        locations:
            - http://bpp.umd.edu/archives/Launches/NS-95_2020-11-07/APRS/W3EAX-10/W3EAX-10_raw_NS95.txt
            - http://bpp.umd.edu/archives/Launches/NS-95_2020-11-07/APRS/W3EAX-11/W3EAX-11_raw_NS95.txt
```

#### listen to a TNC on COM3, watching specific callsigns, and synchronize new packets with a database table via SSH tunnel

```yaml
# config.yaml

callsigns:
    - W3EAX-8
    - W3EAX-14

packets:
    text:
        locations:
            - COM3
    database:
        hostname: localhost
        port: 5432
        database: nearspace
        table: ns110
        username: user1
        password: password1
        tunnel:
            hostname: bpp.umd.edu
            port: 22
            username: user1
            password: password2
```



