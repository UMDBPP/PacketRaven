# PacketRaven

[![tests](https://github.com/UMDBPP/PacketRaven/workflows/tests/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Atests)
[![docs](https://readthedocs.org/projects/packetraven/badge/?version=latest)](https://packetraven.readthedocs.io/en/latest/?badge=latest)
[![license](https://img.shields.io/github/license/umdbpp/packetraven)](https://opensource.org/licenses/MIT)

PacketRaven is a command-line dashboard that retrieves location telemetry sent by high-altitude balloon payloads.
The program is designed to be run during a flight and display information in a terminal user interface (TUI):
![demo](https://github.com/UMDBPP/PacketRaven/blob/main/docs/images/demo.gif)

## Features

- retrieve location telemetry from a variety of sources, including
  - https://amateur.sondehub.org
  - https://aprs.fi
  - a TNC-equipped radio connected via USB
  - a text file containing raw APRS frames
  - a GeoJSON file with telemetry attached to coordinates
- retrieve balloon flight predictions from https://predict.sondehub.org
- plot variables such as altitude and ascent rate over time
- estimate landing time and location

## Installation

[Download an executable file from the latest release.](https://github.com/UMDBPP/PacketRaven/releases)

> **Note**
> Alternatively, you may compile the program yourself:
> ```shell
> git clone https://github.com/UMDBPP/PacketRaven.git
> cd packetraven
> cargo build --release
> ls target/release
> ```

## Usage

First, you need a configuration file. You may use one from the `examples/` directory in this repository, or [write one yourself](https://packetraven.readthedocs.io/en/latest/configuration.html).

Then, run your executable from the terminal with the path to your configuration as the first argument:
```shell
./packetraven_Windows.exe examples/example_1.yaml
```

You should then see the following in your terminal window:
![starting screen](https://github.com/UMDBPP/PacketRaven/blob/main/docs/images/example1_log.png)

The left and right arrow keys (or `Tab` and `Shift+Tab`) cycle through active tabs, 
and the up and down arrow keys change the current plot (or scroll through log messages).
![altitude telemetry plotted over time](https://github.com/UMDBPP/PacketRaven/blob/main/docs/images/example1_altitude.png)

To quit, press `q` or `Esc`.

