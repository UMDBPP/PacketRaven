from datetime import datetime, timedelta

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

    response_json = cusf_api.get()
    predict = cusf_api.predict

    assert all(
        stage in [entry['stage'] for entry in response_json['prediction']]
        for stage in ['ascent', 'descent']
    )
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

    response_json = cusf_api.get()
    predict = cusf_api.predict

    assert all(
        stage in [entry['stage'] for entry in response_json['prediction']]
        for stage in ['ascent', 'descent']
    )
    assert len(predict) > 0


def test_descending_prediction():
    launch_site = (-77.547824, 39.359031, 2000.0)
    launch_datetime = datetime.now()
    ascent_rate = 5.5
    burst_altitude = launch_site[-1] + 0.1
    descent_rate = 9

    cusf_api = CUSFBalloonPredictionQuery(
        launch_site, launch_datetime, ascent_rate, burst_altitude, descent_rate
    )

    response_json = cusf_api.get()
    predict = cusf_api.predict

    assert all(
        stage in [entry['stage'] for entry in response_json['prediction']]
        for stage in ['ascent', 'descent']
    )
    assert len(predict) > 0


def test_float_prediction():
    launch_site = (-77.547824, 39.359031, 2000.0)
    launch_datetime = datetime.now()
    ascent_rate = 5.5
    burst_altitude = 28000
    descent_rate = 9

    cusf_api = CUSFBalloonPredictionQuery(
        launch_site,
        launch_datetime,
        ascent_rate,
        burst_altitude,
        descent_rate,
        float_end_time=datetime.now()
                       + timedelta(seconds=burst_altitude / ascent_rate)
                       + timedelta(hours=1),
    )

    response_json = cusf_api.get()
    predict = cusf_api.predict

    assert all(
        stage in [entry['stage'] for entry in response_json['prediction']]
        for stage in ['ascent', 'float', 'descent']
    )
    assert len(predict) > 0
