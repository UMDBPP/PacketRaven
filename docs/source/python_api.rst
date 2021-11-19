Python API
==========

packet sources and USB / network connections
--------------------------------------------

serial (USB) connection
^^^^^^^^^^^^^^^^^^^^^^^

This class listens for raw APRS frames being sent over USB `in ASCII text`. An example of this is the Kenwood TNC.

.. autoclass:: packetraven.connections.serial.SerialTNC

network connections
^^^^^^^^^^^^^^^^^^^

.. autoclass:: packetraven.connections.internet.APRSfi
.. autoclass:: packetraven.connections.internet.APRSDatabaseTable
.. autoclass:: packetraven.connections.internet.APRSis

file watchers
^^^^^^^^^^^^^

.. autoclass:: packetraven.connections.file.RawAPRSTextFile
.. autoclass:: packetraven.connections.file.PacketGeoJSON

abstract classes
^^^^^^^^^^^^^^^^

.. autoclass:: packetraven.connections.base.Connection
.. autoclass:: packetraven.connections.base.PacketSource
.. autoclass:: packetraven.connections.base.PacketSink
.. autoclass:: packetraven.connections.base.NetworkConnection
.. autoclass:: packetraven.connections.base.APRSPacketSource
.. autoclass:: packetraven.connections.base.APRSPacketSink

graphical user interface (GUI)
------------------------------

GUI class
^^^^^^^^^

.. autoclass:: packetraven.gui.base.PacketRavenGUI

plotting
^^^^^^^^

.. autoclass:: packetraven.gui.plotting.LiveTrackPlot

packets
-------

location packet
^^^^^^^^^^^^^^^

.. autoclass:: packetraven.packets.base.LocationPacket

APRS packet
^^^^^^^^^^^

.. autoclass:: packetraven.packets.base.APRSPacket

packet delta
^^^^^^^^^^^^

.. autoclass:: packetraven.packets.base.Distance

APRS frame parsing
^^^^^^^^^^^^^^^^^^

.. automodule:: packetraven.packets.parsing

packet tracks
-------------

location track
^^^^^^^^^^^^^^

.. autoclass:: packetraven.packets.tracks.LocationPacketTrack

balloon flight track
^^^^^^^^^^^^^^^^^^^^

.. autoclass:: packetraven.packets.tracks.BalloonTrack

APRS track
^^^^^^^^^^

.. autoclass:: packetraven.packets.tracks.APRSTrack

predicted track
^^^^^^^^^^^^^^^

.. autoclass:: packetraven.packets.tracks.PredictedTrajectory

file writer
^^^^^^^^^^^

.. autofunction:: packetraven.packets.writer.write_packet_tracks

underlying data structure
^^^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: packetraven.packets.structures.DoublyLinkedList

balloon flight prediction interface
-----------------------------------

.. autoclass:: packetraven.predicts.BalloonPredictionQuery
.. autoclass:: packetraven.predicts.CUSFBalloonPredictionQuery
.. autoclass:: packetraven.predicts.LukeRenegarBalloonPredictionQuery
