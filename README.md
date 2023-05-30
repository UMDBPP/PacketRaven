PacketRaven
===========

[![tests](https://github.com/UMDBPP/PacketRaven/workflows/tests/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Atests)
[![docs](https://readthedocs.org/projects/packetraven/badge/?version=latest)](https://packetraven.readthedocs.io/en/latest/?badge=latest)
[![license](https://img.shields.io/github/license/umdbpp/packetraven)](https://opensource.org/licenses/MIT)

![demo](https://media.githubusercontent.com/media/UMDBPP/PacketRaven/main/docs/images/demo.gif)

Installation and Usage
----------------------

Download an executable file from the [latest release](https://github.com/UMDBPP/PacketRaven/releases).
Then, open a terminal window and enter the path to teh executable, as well as to a YAML configuration file.
You can modify a configuration from the `examples/` directory, or [write your own](https://packetraven.readthedocs.io/configuration).

For example, to run ``examples/example_1.yaml``, enter the following into your terminal:
   
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
