# `packetraven`

[![tests](https://github.com/UMDBPP/PacketRaven/workflows/tests/badge.svg)](https://github.com/UMDBPP/PacketRaven/actions?query=workflow%3Atests)
[![docs](https://readthedocs.org/projects/packetraven/badge/?version=latest)](https://packetraven.readthedocs.io/en/latest/?badge=latest)
[![license](https://img.shields.io/github/license/umdbpp/packetraven)](https://opensource.org/licenses/MIT)

track high-altitude balloon telemetry with a TNC-equipped radio connected via USB, or from https://amateur.sondehub.org or https://aprs.fi

## Installation

retrieve the latest compiled executable from the [Releases page](https://github.com/UMDBPP/PacketRaven/releases)

---
**NOTE**

Alternatively, you may download the source code and compile the program yourself:

```shell
git clone https://github.com/UMDBPP/PacketRaven.git
cd packetraven
cargo build
```

## Usage

To run ``packetraven``, open a terminal window and type the path to the executable file. 
The program accepts a single argument; the configuration filename.

For example, to run ``packetraven`` on ``examples/example_1.yaml``, run the following:
   
```shell
packetraven examples/example_1.yaml
```

For usage examples, see the `examples/` directory or [view the documentation on ReadTheDocs](https://packetraven.readthedocs.io/en/latest/usage.html).