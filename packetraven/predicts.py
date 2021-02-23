from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Tuple, Union

import requests
from shapely.geometry import Point


class APIURL(Enum):
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
        launch_datetime: datetime,
        ascent_rate: float,
        burst_altitude: float,
        descent_rate: float,
    ):
        """
        initialize a new balloon prediction API query

        :param api_url: URL of API
        :param launch_site:
        :param launch_datetime:
        :param ascent_rate:
        :param burst_altitude:
        :param descent_rate:
        """

        if not isinstance(launch_site, Point):
            launch_site = Point(launch_site)

        self.api_url = api_url
        self.launch_site = launch_site
        self.launch_datetime = launch_datetime
        self.ascent_rate = ascent_rate
        self.burst_altitude = burst_altitude
        self.descent_rate = descent_rate

    @property
    @abstractmethod
    def query(self) -> {str: Any}:
        raise NotImplementedError

    @abstractmethod
    def get(self) -> {str: Any}:
        raise NotImplementedError


class CUSFBalloonPredictionQuery(BalloonPredictionQuery):
    def __init__(
        self,
        launch_site: Union[Tuple[float, float], Point],
        launch_datetime: datetime,
        ascent_rate: float,
        burst_altitude: float,
        descent_rate: float,
        profile: FlightProfile = None,
        version: float = None,
        dataset_datetime: datetime = None,
        api_url: str = APIURL.cusf.value,
    ):
        super().__init__(
            api_url, launch_site, launch_datetime, ascent_rate, burst_altitude, descent_rate
        )

        # CUSF API requires longitude in 0-360 format
        if self.launch_site.x < 0:
            launch_coordinates = [self.launch_site.x + 360, self.launch_site.y]
            if self.launch_site.has_z:
                launch_coordinates.append(self.launch_site.z)
            self.launch_site = Point(launch_coordinates)

        self.profile = profile
        self.version = version
        self.dataset_datetime = dataset_datetime

    @property
    def query(self) -> {str: Any}:
        query = {
            'launch_longitude': self.launch_site.x,
            'launch_latitude': self.launch_site.y,
            'launch_datetime': f'{self.launch_datetime:%Y-%m-%dT%H:%M:%SZ}',
            'ascent_rate': self.ascent_rate,
            'burst_altitude': self.burst_altitude,
            'descent_rate': self.descent_rate,
        }

        if self.launch_site.has_z:
            query['launch_altitude'] = self.launch_site.z
        if self.profile is not None:
            query['profile'] = self.profile.value
        if self.version is not None:
            query['version'] = self.version
        if self.dataset_datetime is not None:
            query['dataset'] = f'{self.dataset_datetime:%Y-%m-%dT%H:%M:%SZ}'

        return query

    def get(self) -> {str: Any}:
        response = requests.get(self.api_url, params=self.query)
        return response.json()


class LukeRenegarBalloonPredictionQuery(CUSFBalloonPredictionQuery):
    def __init__(
        self,
        launch_site: Union[Tuple[float, float], Point],
        launch_datetime: datetime,
        ascent_rate: float,
        burst_altitude: float,
        descent_rate: float,
        ascent_rate_standard_deviation: float = None,
        burst_altitude_standard_deviation: float = None,
        descent_rate_standard_deviation: float = None,
        wind_standard_deviation: float = None,
        use_monte_carlo: bool = None,
        physics_model: str = None,
        profile: FlightProfile = None,
        version: float = None,
        dataset_datetime: datetime = None,
        api_url: str = APIURL.lukerenegar.value,
    ):
        super().__init__(
            launch_site,
            launch_datetime,
            ascent_rate,
            burst_altitude,
            descent_rate,
            profile,
            version,
            dataset_datetime,
            api_url,
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


if __name__ == '__main__':
    launch_site = (-77.547824, 39.359031)
    launch_datetime = datetime.now()
    ascent_rate = 5.5
    burst_altitude = 28000
    descent_rate = 9

    cusf_api = CUSFBalloonPredictionQuery(launch_site, launch_datetime, ascent_rate, burst_altitude, descent_rate)
    json = cusf_api.get()

    print('done')
