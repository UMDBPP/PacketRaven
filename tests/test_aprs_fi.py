import os

import pytest

from packetraven import APRSfi
from packetraven.configuration.credentials import APRSfiCredentials
from packetraven.packets import APRSPacket


@pytest.fixture
def credentials() -> APRSfiCredentials:
    api_key = os.environ.get("APRS_FI_API_KEY")

    return APRSfiCredentials(api_key=api_key)


@pytest.mark.skipif(
    "APRS_FI_API_KEY" not in os.environ,
    reason="no environment variables set for connection information",
)
@pytest.mark.serial
def test_aprs_fi(credentials):
    balloon_callsigns = ["W3EAX-10", "W3EAX-11", "W3EAX-13", "W3EAX-14"]

    aprs_api = APRSfi(balloon_callsigns, api_key=credentials["api_key"])

    packets = aprs_api.packets

    assert all(type(packet) is APRSPacket for packet in packets)
