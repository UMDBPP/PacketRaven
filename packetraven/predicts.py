from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional, Tuple, Union

import pytz
import requests
from shapely.geometry import Point
import typepigeon

from packetraven.packets import LocationPacket
from packetraven.packets.tracks import PredictedTrajectory

DEFAULT_FLOAT_ALTITUDE_UNCERTAINTY = 500
UTC_TIMEZONE = pytz.utc


class PredictionAPIURL(Enum):
    cusf = 'https://predict.cusf.co.uk/api/v1/'
    lukerenegar = 'https://predict.lukerenegar.com/api/v1.1/'


class FlightProfile(Enum):
    standard = 'standard_profile'
    float = 'float_profile'


class BalloonPredictionQuery(ABC):
    """
    balloon prediction API query
    """

    def __init__(
        self,
        api_url: str,
        start_location: Union[Tuple[float, float, Optional[float]], Point],
        start_time: datetime,
        ascent_rate: float,
        burst_altitude: float,
        sea_level_descent_rate: float,
        float_altitude: float = None,
        float_duration: timedelta = None,
        name: str = None,
        descent_only: bool = False,
    ):
        """
        :param api_url: URL of API
        :param start_location: location of balloon launch
        :param start_time: date and time of balloon launch
        :param ascent_rate: average ascent rate (m/s)
        :param burst_altitude: altitude at which balloon will burst
        :param sea_level_descent_rate: descent rate at sea level (m/s)
        :param float_altitude: altitude of float (m)
        :param float_duration: date and time of float end
        :param name: name of prediction track
        :param descent_only: whether to query for descent only
        """

        if not isinstance(start_location, Point):
            start_location = typepigeon.convert_value(start_location, Point)

        if name is None:
            name = 'prediction'

        if start_time is not None:
            if not isinstance(start_time, datetime):
                start_time = typepigeon.convert_value(start_time, datetime)
            if start_time.tzinfo is None or start_time.tzinfo.utcoffset(start_time) is None:
                start_time = UTC_TIMEZONE.localize(start_time)

        if float_duration is not None:
            if not isinstance(float_duration, datetime):
                float_duration = typepigeon.convert_value(float_duration, timedelta)

        self.api_url = api_url
        self.start_location = start_location
        self.start_time = start_time
        self.ascent_rate = ascent_rate
        self.burst_altitude = burst_altitude
        self.sea_level_descent_rate = abs(sea_level_descent_rate)
        self.float_altitude = float_altitude
        self.float_duration = float_duration
        self.name = name
        self.descent_only = descent_only

    @property
    @abstractmethod
    def query(self) -> Dict[str, Any]:
        raise NotImplementedError

    def get(self) -> Dict[str, Any]:
        response = requests.get(self.api_url, params=self.query)
        return response.json()

    @property
    @abstractmethod
    def predict(self) -> PredictedTrajectory:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({repr(self.api_url)}, {repr(self.start_location)}, {repr(self.start_time)}, {repr(self.ascent_rate)}, {repr(self.burst_altitude)}, {repr(self.sea_level_descent_rate)})'


class PredictionError(Exception):
    pass


class CUSFBalloonPredictionQuery(BalloonPredictionQuery):
    """
    connection to https://predict.cusf.co.uk/api/v1/

    >>> cusf_api = CUSFBalloonPredictionQuery(start_location=(-77.547824, 39.359031), launch_datetime=datetime.now(), ascent_rate=5.5, burst_altitude=28000, descent_rate=9)
    >>> predicted_track = cusf_api.predict
    """

    def __init__(
        self,
        start_location: Union[Tuple[float, float, Optional[float]], Point],
        start_time: datetime,
        ascent_rate: float,
        burst_altitude: float,
        sea_level_descent_rate: float,
        profile: FlightProfile = None,
        version: float = None,
        dataset_time: datetime = None,
        float_altitude: float = None,
        float_duration: timedelta = None,
        api_url: PredictionAPIURL = None,
        name: str = None,
        descent_only: bool = False,
    ):
        if profile is None:
            if not descent_only and (float_altitude is not None or float_duration is not None):
                profile = FlightProfile.float
            else:
                profile = FlightProfile.standard

        if dataset_time is not None:
            if not isinstance(dataset_time, datetime):
                dataset_time = typepigeon.convert_value(dataset_time, datetime)
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
            start_location,
            start_time,
            ascent_rate,
            burst_altitude,
            sea_level_descent_rate,
            float_altitude,
            float_duration,
            name,
            descent_only,
        )

        # CUSF API requires longitude in 0-360 format
        if self.start_location.x < 0:
            x = self.start_location.x + 360
        else:
            x = self.start_location.x
        launch_coordinates = [x, self.start_location.y]
        if self.start_location.has_z:
            launch_coordinates.append(self.start_location.z)
        self.launch_site = Point(launch_coordinates)

        self.profile = profile if not self.descent_only else FlightProfile.standard
        self.version = version
        self.dataset_time = dataset_time

    @property
    def query(self) -> Dict[str, Any]:
        query = {
            'launch_longitude': self.launch_site.x,
            'launch_latitude': self.launch_site.y,
            'launch_datetime': self.start_time.isoformat(),
            'ascent_rate': self.ascent_rate,
            'burst_altitude': self.burst_altitude
            if not self.descent_only
            else self.launch_site.z + 1,
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

        if self.profile == FlightProfile.float and not self.descent_only:
            if self.float_altitude is None:
                self.float_altitude = self.burst_altitude
            if self.float_duration is None:
                raise PredictionError('float duration not provided')
            query['float_altitude'] = self.float_altitude
            start_altitude = self.start_location.z if self.start_location.has_z else 0
            float_start_time = self.start_time + timedelta(
                seconds=(self.float_altitude - start_altitude) / self.ascent_rate
            )
            query['stop_datetime'] = (float_start_time + self.float_duration).isoformat()

        return query

    def get(self) -> Dict[str, Any]:
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
                            start_location=[
                                float_end['longitude'],
                                float_end['latitude'],
                                float_end['altitude'],
                            ],
                            start_time=typepigeon.convert_value(
                                float_end['datetime'], datetime
                            ),
                            ascent_rate=10,
                            burst_altitude=float_end['altitude'] + 0.1,
                            sea_level_descent_rate=self.sea_level_descent_rate,
                            profile=FlightProfile.standard,
                            version=self.version,
                            dataset_time=self.dataset_time,
                            float_altitude=None,
                            float_duration=None,
                            api_url=self.api_url,
                            name=self.name,
                            descent_only=True,
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
            try:
                error = response.json()['error']['description']
            except:
                error = 'no message'
            raise ConnectionError(
                f'connection raised error {response.status_code} for {response.url} - {error}'
            )

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
                packets=[
                    LocationPacket(
                        point['datetime'],
                        point['longitude'],
                        point['latitude'],
                        point['altitude'],
                    )
                    for point in points
                ],
                parameters=response['request'],
                metadata=response['metadata'],
            )
        else:
            raise PredictionError(response['error']['description'])


class LukeRenegarBalloonPredictionQuery(CUSFBalloonPredictionQuery):
    """
    connection to https://predict.lukerenegar.com/api/v1.1/
    """

    def __init__(
        self,
        start_location: Union[Tuple[float, float, Optional[float]], Point],
        start_time: datetime,
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
        float_duration: timedelta = None,
        api_url: str = None,
        name: str = None,
        descent_only: bool = False,
    ):
        if api_url is None:
            api_url = PredictionAPIURL.lukerenegar

        if name is None:
            name = 'lrenegar_prediction'

        super().__init__(
            start_location,
            start_time,
            ascent_rate,
            burst_altitude,
            sea_level_descent_rate,
            profile,
            version,
            dataset_time,
            float_altitude,
            float_duration,
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
    def query(self) -> Dict[str, Any]:
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
