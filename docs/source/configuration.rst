Configuration File
==================

``packetraven`` reads a YAML configuration file as input. All units are in SI.

.. literalinclude:: ../../examples/example_3.yaml
   :language: yaml

Entries
-------

``callsigns``
^^^^^^^^^^^^^

a list of callsigns as strings, including SSIDs if present

.. code-block:: yaml

   callsigns:
     - W3EAX-9
     - W3EAX-11
     - W3EAX-12

``time``
^^^^^^^^

start and end times by which to filter received telemetry, along with the interval that ``packetraven`` fetches new telemetry

.. code-block:: yaml

   time:
     start: 2022-03-05 00:00:00
     end: 2022-03-06 00:00:00
     interval: 120

``output_file``
^^^^^^^^^^^^^^^

GeoJSON file to output telemetry to

.. code-block:: yaml

   output_file: example_3.geojson

``connections``
^^^^^^^^^^^^^^^

connections from which to retrieve packets

.. code-block:: yaml

   connections:
     sondehub: {}
     aprs_fi: 
       api_key: 123456.abcdefhijklmnop
     text:
       - port: /dev/ttyUSB0
         baud_rate: 9600
       - path: ~/packets.txt

.. note::
   To define a connection with no options (i.e. the ``sondehub`` entry, above), use YAML's empty flow mapping syntax ``sondehub: {}``.
   The empty block mapping syntax (``sondehub: ``) is equivalent to ``sondehub: null`` and will not initiate the connection.

``prediction``
^^^^^^^^^^^^^^

prediction profile for all callsigns

.. code-block:: yaml

   prediction:
     start:
       coord:
         x: -78.4987
         y: 40.0157
       time: 2022-03-05 10:36:00
     profile:
       ascent_rate: 6.5
       burst_altitude: 25000
       sea_level_descent_rate: 9
     float:
       duration: 3600
       float_altitude: 25000
       uncertainty: 500
     output_file: example_3_prediction.geojson

Examples
--------

Example 1
^^^^^^^^^

watch text file(s) for new lines containing raw APRS frames

.. literalinclude:: ../../examples/example_1.yaml
   :language: yaml

Example 2
^^^^^^^^^

listen to a TNC-equipped radio plugged into USB COM3, poll https://amateur.sondehub.org and https://aprs.fi

.. literalinclude:: ../../examples/example_2.yaml
   :language: yaml


Example 3
^^^^^^^^^

do a bunch of stuff

.. literalinclude:: ../../examples/example_3.yaml
   :language: yaml


