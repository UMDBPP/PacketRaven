examples
========

``examples/example_1.yaml``
---------------------------

watch text file(s) for new lines containing raw APRS frames

.. literalinclude:: ../../examples/example_1.yaml
   :language: yaml

``examples/example_2.yaml``
---------------------------

listen to a TNC-equipped radio connected to port ``COM3`` and poll https://amateur.sondehub.org and https://aprs.fi

.. literalinclude:: ../../examples/example_2.yaml
   :language: yaml

``examples/example_3.yaml``
---------------------------

retrieve telemetry from https://amateur.sondehub.org, 
a TNC-equipped radio connected to port ``/dev/ttyUSB0``, and a text file
every 120 seconds, filtering by specific callsigns and a specific time range;
additionally, retrieve CUSF predictions following the given profile and output telemetry data to a GeoJSON file

.. literalinclude:: ../../examples/example_3.yaml
   :language: yaml

