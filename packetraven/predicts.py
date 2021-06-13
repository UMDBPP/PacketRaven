from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional, Tuple, Union

from dateutil.parser import parse as parse_date
import numpy
import pytz
import requests
from shapely.geometry import Point

from packetraven.packets import LocationPacket
from packetraven.packets.tracks import LocationPacketTrack, PredictedTrajectory
from packetraven.utilities import get_logger

DEFAULT_ASCENT_RATE = 5.5
DEFAULT_BURST_ALTITUDE = 28000
DEFAULT_SEA_LEVEL_DESCENT_RATE = 9
UTC_TIMEZONE = pytz.utc

LOGGER = get_logger('predicts')


class PredictionAPIURL(Enum):
    cusf = 'https://predict.cusf.co.uk/api/v1/'
    lukerenegar = 'https://predict.lukerenegar.com/api/v1.1/'


class FlightProfile(Enum):
    standard = 'standard_profile'
    float = 'float_profile'


class BalloonPredictionQuery(ABC):
    def __init__(
        self,
        api_url: str,
        launch_site: Union[Tuple[float, float, Optional[float]], Point],
        launch_time: datetime,
        ascent_rate: float,
        burst_altitude: float,
        sea_level_descent_rate: float,
        float_altitude: float = None,
        float_end_time: datetime = None,
        name: str = None,
        descent_only: bool = False,
    ):
        """
        initialize a new balloon prediction API query

        :param api_url: URL of API
        :param launch_site: location of balloon launch
        :param launch_time: date and time of balloon launch
        :param ascent_rate: average ascent rate (m/s)
        :param burst_altitude: altitude at which balloon will burst
        :param sea_level_descent_rate: descent rate at sea level (m/s)
        :param float_altitude: altitude of float (m)
        :param float_end_time: date and time of float end
        :param name: name of prediction track
        :param descent_only: whether to query for descent only
        """

        if not isinstance(launch_site, Point):
            launch_site = Point(launch_site)

        if name is None:
            name = 'prediction'

        if launch_time is not None:
            if launch_time.tzinfo is None or launch_time.tzinfo.utcoffset(launch_time) is None:
                launch_time = UTC_TIMEZONE.localize(launch_time)

        if float_end_time is not None:
            if (
                float_end_time.tzinfo is None
                or float_end_time.tzinfo.utcoffset(float_end_time) is None
            ):
                float_end_time = UTC_TIMEZONE.localize(float_end_time)

        self.api_url = api_url
        self.launch_site = launch_site
        self.launch_time = launch_time
        self.ascent_rate = ascent_rate
        self.burst_altitude = burst_altitude
        self.sea_level_descent_rate = sea_level_descent_rate
        self.float_altitude = float_altitude
        self.float_end_time = float_end_time
        self.name = name
        self.descent_only = descent_only

    @property
    @abstractmethod
    def query(self) -> {str: Any}:
        raise NotImplementedError

    def get(self) -> {str: Any}:
        response = requests.get(self.api_url, params=self.query)
        return response.json()

    @property
    @abstractmethod
    def predict(self) -> PredictedTrajectory:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({repr(self.api_url)}, {repr(self.launch_site)}, {repr(self.launch_time)}, {repr(self.ascent_rate)}, {repr(self.burst_altitude)}, {repr(self.sea_level_descent_rate)})'


class PredictionError(Exception):
    pass


class CUSFBalloonPredictionQuery(BalloonPredictionQuery):
    def __init__(
        self,
        launch_site: Union[Tuple[float, float], Point],
        launch_time: datetime,
        ascent_rate: float,
        burst_altitude: float,
        sea_level_descent_rate: float,
        profile: FlightProfile = None,
        version: float = None,
        dataset_time: datetime = None,
        float_altitude: float = None,
        float_end_time: datetime = None,
        api_url: PredictionAPIURL = None,
        name: str = None,
        descent_only: bool = False,
    ):
        if profile is None:
            if float_altitude is not None or float_end_time is not None:
                profile = FlightProfile.float
            else:
                profile = FlightProfile.standard

        if dataset_time is not None:
            if (
                dataset_time.tzinfo is None
                or dataset_time.tzinfo.utcoffset(dataset_time) is None
            ):
                dataset_time = UTC_TIMEZONE.localize(dataset_time)

        if api_url is None:
            api_url = PredictionAPIURL.cusf

        if isinstance(api_url, PredictionAPIURL):
            api_url = api_url.value

        if name is None:
            name = 'cusf_prediction'

        super().__init__(
            api_url,
            launch_site,
            launch_time,
            ascent_rate,
            burst_altitude,
            sea_level_descent_rate,
            float_altitude,
            float_end_time,
            name,
            descent_only,
        )

        # CUSF API requires longitude in 0-360 format
        if self.launch_site.x < 0:
            launch_coordinates = [self.launch_site.x + 360, self.launch_site.y]
            if self.launch_site.has_z:
                launch_coordinates.append(self.launch_site.z)
            self.launch_site = Point(launch_coordinates)

        self.profile = profile if not self.descent_only else FlightProfile.standard
        self.version = version
        self.dataset_time = dataset_time

    @property
    def query(self) -> {str: Any}:
        query = {
            'launch_longitude': self.launch_site.x,
            'launch_latitude': self.launch_site.y,
            'launch_datetime': self.launch_time.isoformat(),
            'ascent_rate': self.ascent_rate,
            'burst_altitude': self.burst_altitude,
            'descent_rate': self.sea_level_descent_rate,
        }

        if self.launch_site.has_z:
            query['launch_altitude'] = self.launch_site.z
        if self.profile is not None:
            query['profile'] = self.profile.value
        if self.version is not None:
            query['version'] = self.version
        if self.dataset_time is not None:
            query['dataset'] = self.dataset_time.isoformat()

        if self.profile == FlightProfile.float:
            if self.float_altitude is None:
                self.float_altitude = self.burst_altitude
            if self.float_end_time is None:
                raise PredictionError('float stop time `float_end_time` not provided')
            query['float_altitude'] = self.float_altitude
            query['stop_datetime'] = self.float_end_time.isoformat()

        return query

    def get(self) -> {str: Any}:
        response = requests.get(self.api_url, params=self.query)

        if response.status_code == 200:
            response = response.json()
            if 'error' not in response:
                # TODO tawhiri currently does not include descent when querying a float profile
                if self.profile == FlightProfile.float:
                    # this code runs another prediction query with a standard profile and extracts the descent stage to append to the response from the original query
                    for stage in response['prediction']:
                        # if a descent stage exists, we don't need to do anything
                        if stage['stage'] == 'descent':
                            break
                    else:
                        for stage in response['prediction']:
                            if stage['stage'] == 'float':
                                float_end = stage['trajectory'][-1]
                                break
                        else:
                            raise PredictionError('API did not return a float trajectory')

                        standard_profile_query = self.__class__(
                            launch_site=[
                                float_end['longitude'],
                                float_end['latitude'],
                                float_end['altitude'],
                            ],
                            launch_time=parse_date(float_end['datetime']),
                            ascent_rate=10,
                            burst_altitude=float_end['altitude'] + 0.1,
                            sea_level_descent_rate=self.sea_level_descent_rate,
                            profile=FlightProfile.standard,
                            version=self.version,
                            dataset_time=self.dataset_time,
                            float_altitude=None,
                            float_end_time=None,
                            api_url=self.api_url,
                            name=self.name,
                        )

                        for stage in standard_profile_query.get()['prediction']:
                            if stage['stage'] == 'descent':
                                response['prediction'].append(stage)
                                break

                if self.descent_only:
                    indices_to_remove = []
                    for index, stage in enumerate(response['prediction']):
                        # if a descent stage exists, we don't need to do anything
                        if stage['stage'] != 'descent':
                            indices_to_remove.append(index)
                            break
                    for index in indices_to_remove:
                        response['prediction'].pop(index)

                return response
            else:
                raise PredictionError(response['error']['description'])
        else:
            raise ConnectionError(f'connection raised error {response.status_code}')

    @property
    def predict(self) -> PredictedTrajectory:
        response = self.get()

        if 'error' not in response:
            points = []

            for stage in response['prediction']:
                points.extend(stage['trajectory'])

            for point in points:
                if point['longitude'] > 180:
                    point['longitude'] -= 360

            return PredictedTrajectory(
                name=self.name,
                packets=[
                    LocationPacket(
                        point['datetime'],
                        point['longitude'],
                        point['latitude'],
                        point['altitude'],
                    )
                    for point in points
                ],
                prediction_time=response['metadata']['complete_datetime'],
            )
        else:
            raise PredictionError(response['error']['description'])


class LukeRenegarBalloonPredictionQuery(CUSFBalloonPredictionQuery):
    def __init__(
        self,
        launch_site: Union[Tuple[float, float], Point],
        launch_time: datetime,
        ascent_rate: float,
        burst_altitude: float,
        sea_level_descent_rate: float,
        ascent_rate_standard_deviation: float = None,
        burst_altitude_standard_deviation: float = None,
        descent_rate_standard_deviation: float = None,
        wind_standard_deviation: float = None,
        use_monte_carlo: bool = None,
        physics_model: str = None,
        profile: FlightProfile = None,
        version: float = None,
        dataset_time: datetime = None,
        float_altitude: float = None,
        float_end_time: datetime = None,
        api_url: str = None,
        name: str = None,
        descent_only: bool = False,
    ):
        if api_url is None:
            api_url = PredictionAPIURL.lukerenegar

        if name is None:
            name = 'lrenegar_prediction'

        super().__init__(
            launch_site,
            launch_time,
            ascent_rate,
            burst_altitude,
            sea_level_descent_rate,
            profile,
            version,
            dataset_time,
            float_altitude,
            float_end_time,
            api_url,
            name,
            descent_only,
        )

        self.ascent_rate_standard_deviation = ascent_rate_standard_deviation
        self.burst_altitude_standard_deviation = burst_altitude_standard_deviation
        self.descent_rate_standard_deviation = descent_rate_standard_deviation
        self.wind_standard_deviation = wind_standard_deviation
        self.use_monte_carlo = use_monte_carlo
        self.physics_model = physics_model

    @property
    def query(self):
        query = super().query

        if self.ascent_rate_standard_deviation is not None:
            query['ascent_rate_std_dev'] = self.ascent_rate_standard_deviation
        if self.burst_altitude_standard_deviation is not None:
            query['burst_altitude_std_dev'] = self.burst_altitude_standard_deviation
        if self.descent_rate_standard_deviation is not None:
            query['descent_rate_std_dev'] = self.descent_rate_standard_deviation
        if self.wind_standard_deviation is not None:
            query['wind_std_dev'] = self.wind_standard_deviation
        if self.use_monte_carlo is not None:
            query['monte_carlo'] = self.use_monte_carlo
        if self.physics_model is not None:
            query['physics_model'] = self.physics_model

        return query


def get_predictions(
    packet_tracks: {str: LocationPacketTrack},
    ascent_rate: float = None,
    burst_altitude: float = None,
    sea_level_descent_rate: float = None,
    float_altitude: float = None,
    float_altitude_uncertainty: float = 500,
    float_duration: timedelta = None,
    api_url: str = None,
) -> [PredictedTrajectory]:
    """
    Return location tracks detailing predicted trajectory of balloon flight(s) from current location.

    :param packet_tracks: location packet tracks
    :param ascent_rate: ascent rate (m/s)
    :param burst_altitude: altitude at which balloon will burst (m)
    :param sea_level_descent_rate: descent rate of payload at sea level (m/s)
    :param float_altitude: altitude at which to float (m)
    :param float_altitude_uncertainty: tolerance around which to consider the balloon "at float altitude"
    :param float_duration: expected duration of float
    :param api_url: URL of prediction API to use
    """

    if api_url is None:
        api_url = PredictionAPIURL.cusf

    if float_altitude is not None and float_duration is None:
        raise ValueError('`float_duration` was not provided')

    if float_duration is not None and float_altitude is None:
        float_altitude = burst_altitude

    prediction_tracks = {}
    for name, packet_track in packet_tracks.items():
        ascent_rates = packet_track.ascent_rates
        if ascent_rate is None:
            average_ascent_rate = ascent_rates[ascent_rates > 0]
            if average_ascent_rate > 0:
                ascent_rate = average_ascent_rate
            else:
                ascent_rate = DEFAULT_ASCENT_RATE
        if burst_altitude is None:
            burst_altitude = DEFAULT_BURST_ALTITUDE
        if sea_level_descent_rate is None:
            sea_level_descent_rate = DEFAULT_SEA_LEVEL_DESCENT_RATE

        if len(ascent_rates) > 2 and all(ascent_rates[-2:] < 0):
            burst_altitude = packet_track.altitudes[-1] + 1

        prediction_start_location = packet_track[-1].coordinates
        prediction_start_time = packet_track[-1].time

        if float_altitude is not None and not packet_track.falling:
            packets_at_float_altitude = packet_track[
                numpy.abs(float_altitude - packet_track.altitudes) < float_altitude_uncertainty
            ]
            if (
                len(packets_at_float_altitude) > 0
                and packets_at_float_altitude[-1].time == packet_track.times[-1]
            ):
                float_start_time = packets_at_float_altitude[0].time
                descent_only = False
            elif packet_track.ascent_rates[-1] >= 0:
                float_start_time = prediction_start_time + timedelta(
                    seconds=(float_altitude - prediction_start_location[2]) / ascent_rate
                )
                descent_only = False
            else:
                float_start_time = None
                descent_only = True
            if float_start_time is not None:
                float_end_time = float_start_time + float_duration
            else:
                float_end_time = None
        else:
            float_end_time = None
            descent_only = packet_track.falling or packet_track.ascent_rates[-1] < 0

        prediction_query = CUSFBalloonPredictionQuery(
            launch_site=prediction_start_location,
            launch_time=prediction_start_time,
            ascent_rate=ascent_rate,
            burst_altitude=burst_altitude,
            sea_level_descent_rate=sea_level_descent_rate,
            float_altitude=float_altitude,
            float_end_time=float_end_time,
            api_url=api_url,
            name=name,
            descent_only=descent_only,
        )

        prediction = prediction_query.predict

        if packet_track.time_to_ground >= timedelta(seconds=0):
            LOGGER.info(
                f'"{packet_track.name}" predicted landing location: {prediction.coordinates[-1]}'
            )

        prediction_tracks[name] = prediction

    return prediction_tracks
