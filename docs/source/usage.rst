Usage Examples
==============

``packetraven`` can read a YAML configuration file in the following format:

.. literalinclude:: ../../examples/example_3.yaml
   :language: yaml

For instance, to listen to a TNC-equipped radio plugged into USB COM3, poll https://amateur.sondehub.org and https://aprs.fi, and only display the callsigns ``KC3SKW-8`` and ``KC3SKW-9``:

.. literalinclude:: ../../examples/example_2.yaml
   :language: yaml

.. note::
   To define a connection with no options (i.e. the ``sondehub`` entry, above), use YAML's empty flow mapping syntax ``sondehub: {}``.
   The empty block mapping syntax (``sondehub: ``) is equivalent to ``sondehub: null`` and will not initiate the connection.

or to watch text file(s) for new lines containing raw APRS frames:

.. literalinclude:: ../../examples/example_1.yaml
   :language: yaml
