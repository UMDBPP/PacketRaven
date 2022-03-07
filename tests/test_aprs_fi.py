from packetraven import APRSfi
from packetraven.packets import APRSPacket

# noinspection PyUnresolvedReferences
from tests import credentials


def test_aprs_fi(credentials):
    balloon_callsigns = ['W3EAX-10', 'W3EAX-11', 'W3EAX-13', 'W3EAX-14']

    aprs_api = APRSfi(balloon_callsigns, credentials['aprs_fi']['api_key'])

    packets = aprs_api.packets

    assert all(type(packet) is APRSPacket for packet in packets)
