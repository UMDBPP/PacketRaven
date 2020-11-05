from packetraven import APRSfi
from packetraven.packets import APRSPacket
from packetraven.utilities import read_configuration, repository_root

CREDENTIALS_FILENAME = repository_root() / 'credentials.config'


def test_aprs_fi():
    balloon_callsigns = ['W3EAX-10', 'W3EAX-11', 'W3EAX-13', 'W3EAX-14']

    credentials = read_configuration(CREDENTIALS_FILENAME)
    if 'aprs_fi' not in credentials:
        credentials['aprs_fi'] = {'api_key': os.environ['APRS_FI_API_KEY']}

    aprs_api = APRSfi(balloon_callsigns, credentials['aprs_fi']['api_key'])

    packets = aprs_api.packets

    assert all(type(packet) is APRSPacket for packet in packets)
