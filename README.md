# PacketRaven

[![tests](https://github.com/UMDBPP/PacketRaven/workflows/tests/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Atests)
[![build](https://github.com/UMDBPP/PacketRaven/workflows/build/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Abuild)
[![license](https://img.shields.io/github/license/umdbpp/packetraven)](https://opensource.org/licenses/MIT)

PacketRaven is a dashboard built to track high-altitude balloon flights from their location telemetry.

## Installation

retrieve the latest binary from the [Releases page](https://github.com/UMDBPP/PacketRaven/releases)

---
**NOTE**

Alternatively, you may download the source code and build the program with Cargo:

```shell
git clone https://github.com/UMDBPP/PacketRaven.git
cd packetraven
cargo build
```

---

## Usage

PacketRaven reads a configuration file to determine which connections to set up, how to parse your packets, which callsigns to filter, etc.

```shell
packetraven examples/example_1.yaml
```

## Examples

#### listen to a TNC sending raw APRS strings over USB port COM4

```yaml
packets:
    text:
        - port: COM4
          baud_rate: 9600
```

#### listen to APRS.fi, watching specific callsigns

you need an API key to connect to APRS.fi; you can get one from https://aprs.fi/page/api

```yaml
callsigns:
    - W3EAX-8
    - W3EAX-14

packets:
    aprs_fi:
        api_key: 123456.abcdefhijklmnop
```

#### watch text file(s) for new lines containing raw APRS strings

```yaml
packets:
    text:
        - path: http://bpp.umd.edu/archives/Launches/NS-95_2020-11-07/APRS/W3EAX-10/W3EAX-10_raw_NS95.txt
        - path: http://bpp.umd.edu/archives/Launches/NS-95_2020-11-07/APRS/W3EAX-11/W3EAX-11_raw_NS95.txt
```

