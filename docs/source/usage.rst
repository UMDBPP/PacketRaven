Usage Examples
==============

``packetraven`` can read a YAML configuration file in the following format:

.. literalinclude:: ../../examples/example_3.yaml
   :language: yaml

For instance, to listen to a TNC-equipped radio plugged into USB COM3, poll https://amateur.sondehub.org and https://aprs.fi, and only display the callsigns ``KC3SKW-8`` and ``KC3SKW-9``:

.. literalinclude:: ../../examples/example_2.yaml
   :language: yaml

or to watch text file(s) for new lines containing raw APRS frames:

.. literalinclude:: ../../examples/example_1.yaml
   :language: yaml
