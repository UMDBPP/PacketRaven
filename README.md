PacketRaven
===========

[![tests](https://github.com/UMDBPP/PacketRaven/workflows/tests/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Atests)
[![docs](https://readthedocs.org/projects/packetraven/badge/?version=latest)](https://packetraven.readthedocs.io/en/latest/?badge=latest)
[![license](https://img.shields.io/github/license/umdbpp/packetraven)](https://opensource.org/licenses/MIT)

![demo](https://media.githubusercontent.com/media/UMDBPP/PacketRaven/main/docs/images/demo.gif)

Installation and Usage
----------------------

Download an executable from the [latest release](https://github.com/UMDBPP/PacketRaven/releases)
and run it from the terminal, passing the path to a 
[configuration file](https://packetraven.readthedocs.io/en/latest/configuration.html).

```shell
./packetraven_Windows.exe examples/example_1.yaml
```
![starting screen](https://media.githubusercontent.com/media/UMDBPP/PacketRaven/main/docs/images/example1_log.png)

The left and right arrow keys (or `Tab` and `Shift+Tab`) cycle through active tabs, 
and the up and down arrow keys change the current plot (or scroll through log messages).
![altitude telemetry plotted over time](https://media.githubusercontent.com/media/UMDBPP/PacketRaven/main/docs/images/example1_altitude.png)

To quit, press `q` or `Esc`.

> **Note**
> Alternatively, you may build the executable yourself with Cargo:
> ```shell
> git clone https://github.com/UMDBPP/PacketRaven.git
> cd packetraven
> cargo build --release
> ls target/release
> ```
