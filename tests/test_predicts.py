from datetime import datetime

from packetraven.predicts import CUSFBalloonPredictionQuery


def test_ground_prediction():
    launch_site = (-77.547824, 39.359031)
    launch_datetime = datetime.now()
    ascent_rate = 5.5
    burst_altitude = 28000
    descent_rate = 9

    cusf_api = CUSFBalloonPredictionQuery(
        launch_site, launch_datetime, ascent_rate, burst_altitude, descent_rate
    )
    predict = cusf_api.predict

    assert len(predict) > 0


def test_ascending_prediction():
    launch_site = (-77.547824, 39.359031, 2000.0)
    launch_datetime = datetime.now()
    ascent_rate = 5.5
    burst_altitude = 28000
    descent_rate = 9

    cusf_api = CUSFBalloonPredictionQuery(
        launch_site, launch_datetime, ascent_rate, burst_altitude, descent_rate
    )
    predict = cusf_api.predict

    assert len(predict) > 0


def test_descending_prediction():
    launch_site = (-77.547824, 39.359031, 2000.0)
    launch_datetime = datetime.now()
    ascent_rate = 5.5
    burst_altitude = launch_site[-1] + 1
    descent_rate = 9

    cusf_api = CUSFBalloonPredictionQuery(
        launch_site, launch_datetime, ascent_rate, burst_altitude, descent_rate
    )
    predict = cusf_api.predict

    assert len(predict) > 0
