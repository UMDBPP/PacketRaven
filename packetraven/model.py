from dateutil.parser import parse as parse_date
from matplotlib import pyplot, quiver
import numpy
import pyproj
from pyproj import CRS, Transformer
import xarray as xarray

WGS84 = CRS.from_epsg(4326)
WEB_MERCATOR = CRS.from_epsg(3857)

# `dh/dt` based on historical flight data
FREEFALL_DESCENT_RATE = lambda altitude: -5.8e-08 * altitude ** 2 - 6.001
# TODO: propagate uncertainty
FREEFALL_DESCENT_RATE_UNCERTAINTY = lambda altitude: 0.2 * FREEFALL_DESCENT_RATE(altitude)

# integration of `(1/(dh/dt)) dh` based on historical flight data
# TODO make this model better with ML
FREEFALL_SECONDS_TO_GROUND = lambda altitude: 1695.02 * numpy.arctan(9.8311e-5 * altitude)
from datetime import datetime, timedelta


class VectorField:
    """
    Vector field of (u, v) values.
    """

    def __init__(self, time_deltas: [timedelta], crs: CRS = None):
        """
        Build vector field of (u, v) values.

        :param time_deltas: list of time deltas
        :param crs: native CRS of field
        """

        if crs is None:
            crs = WGS84
        if not isinstance(time_deltas, numpy.ndarray) or time_deltas.dtype != numpy.timedelta64:
            time_deltas = numpy.array(time_deltas, dtype='timedelta64[s]')
        self.time_deltas = time_deltas
        self.crs = crs

        time_delta = numpy.nanmean(self.time_deltas).item()
        if type(time_delta) is int:
            time_delta *= 1e-9
        elif type(time_delta) is timedelta:
            time_delta = int(time_delta / timedelta(seconds=1))

        self.delta_t = timedelta(seconds=time_delta)

    def u(self, point: numpy.array, time: datetime) -> float:
        """
        u velocity in m/s at coordinates

        :param point: coordinates in linear units
        :param time: time
        :return: u value at coordinate in m/s
        """

        pass

    def v(self, point: numpy.array, time: datetime) -> float:
        """
        v velocity in m/s at coordinates

        :param point: lon / lat coordinates
        :param time: time
        :return: v value at coordinate in m/s
        """

        pass

    def velocity(self, point: numpy.array, time: datetime) -> float:
        """
        absolute velocity in m/s at coordinate

        :param point: lon / lat coordinates
        :param time: time
        :return: magnitude of uv vector in m/s
        """

        return numpy.sqrt(self.u(point, time) ** 2 + self.v(point, time) ** 2)

    def direction(self, point: numpy.array, time: datetime) -> float:
        """
        angle of uv vector

        :param point: lon / lat coordinates
        :param time: time
        :return: radians from east of uv vector
        """

        return numpy.arctan2(self.u(point, time), self.v(point, time))

    def plot(self, time: datetime, axis: pyplot.Axes = None, **kwargs) -> quiver.Quiver:
        """
        Plot vector field at the given time.

        :param time: time at which to plot
        :param axis: pyplot axis on which to plot
        :return: quiver plot
        """

        pass

    def __getitem__(self, position: (numpy.array, datetime)) -> numpy.array:
        """
        velocity vector (u, v) in m/s at coordinates

        :param point: coordinates in linear units
        :param time: time
        :return: (u, v) vector
        """

        point, time = position
        vector = numpy.array([self.u(point, time), self.v(point, time)])
        vector[numpy.isnan(vector)] = 0
        return vector

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({repr(self.delta_t)})'


class RankineVortex(VectorField):
    """
    Time-invariant circular vector field moving in solid-body rotation (like a turntable).
    """

    def __init__(
        self,
        center: (float, float),
        radius: float,
        period: timedelta,
        time_deltas: numpy.array,
    ):
        """
        Construct a 2-dimensional solid rotating disk surrounded by inverse falloff of tangential velocity.

        :param center: tuple of geographic coordinates
        :param radius: radius of central solid rotation in meters
        :param period: rotational period
        :param time_deltas: time differences
        """

        transformer = Transformer.from_crs(WGS84, WEB_MERCATOR)
        self.center = numpy.array(transformer.transform(*center))
        self.radius = radius
        self.angular_velocity = 2 * numpy.pi / (period / timedelta(seconds=1))

        super().__init__(time_deltas)

    def u(self, point: numpy.array, time: datetime) -> float:
        return -self.velocity(point, time) * numpy.cos(numpy.arctan2(*(point - self.center)))

    def v(self, point: numpy.array, time: datetime) -> float:
        return self.velocity(point, time) * numpy.sin(numpy.arctan2(*(point - self.center)))

    def velocity(self, point: numpy.array, time: datetime) -> float:
        radial_distance = numpy.sqrt(numpy.sum((point - self.center) ** 2))

        if radial_distance <= self.radius:
            return self.angular_velocity * radial_distance
        else:
            return self.angular_velocity * self.radius ** 2 / radial_distance

    def plot(self, axis: pyplot.Axes = None, **kwargs) -> quiver.Quiver:
        if axis is None:
            axis = pyplot.axes()

        points = []
        radii = numpy.linspace(1, self.radius * 2, 20)

        for radius in radii:
            num_points = 50
            points.extend(
                [
                    (
                        numpy.cos(2 * numpy.pi / num_points * point_index) * radius
                        + self.center[0],
                        numpy.sin(2 * numpy.pi / num_points * point_index) * radius
                        + self.center[1],
                    )
                    for point_index in range(0, num_points + 1)
                ]
            )

        vectors = [self[point, datetime.now()] for point in points]
        points = list(
            zip(*pyproj.transform(WEB_MERCATOR, WGS84, *zip(*points)))
        )

        quiver_plot = axis.quiver(*zip(*points), *zip(*vectors), units='width', **kwargs)
        axis.quiverkey(
            quiver_plot, 0.9, 0.9, 1, r'$1 \frac{m}{s}$', labelpos='E', coordinates='figure'
        )

        return quiver_plot


class VectorDataset(VectorField):
    """
    Vector field with time component using xarray observation.
    """

    def __init__(
        self,
        dataset: xarray.Dataset,
        u_name: str = None,
        v_name: str = None,
        x_name: str = None,
        y_name: str = None,
        z_name: str = None,
        t_name: str = None,
        coordinate_system: CRS = None,
    ):
        """
        Create new velocity field from given observation.

        :param dataset: xarray observation containing velocity data (u, v)
        :param u_name: name of u variable
        :param v_name: name of v variable
        :param x_name: name of x coordinate
        :param y_name: name of y coordinate
        :param z_name: name of z coordinate
        :param t_name: name of time coordinate
        :param coordinate_system: coordinate system of observation
        """

        if coordinate_system is None:
            coordinate_system = WGS84

        self.coordinate_system = coordinate_system

        if u_name is None:
            u_name = 'u'
        if v_name is None:
            v_name = 'v'
        if x_name is None:
            x_name = 'lon'
        if y_name is None:
            y_name = 'lat'
        if z_name is None:
            z_name = 'z'
        if t_name is None:
            t_name = 'time'

        self.u_name = u_name
        self.v_name = v_name
        self.x_name = x_name
        self.y_name = y_name
        self.z_name = z_name
        self.t_name = t_name

        self.dataset = dataset

        self.delta_x = numpy.mean(numpy.diff(self.dataset[self.x_name]))
        self.delta_y = numpy.mean(numpy.diff(self.dataset[self.x_name]))

        super().__init__(numpy.diff(self.dataset[self.t_name].values))

    def _interpolate(self, variable: str, point: numpy.array, time: datetime) -> xarray.DataArray:
        if not isinstance(point, numpy.ndarray):
            point = numpy.array(point)
        if isinstance(time, str):
            time = parse_date(time)
        elif isinstance(time, timedelta):
            time += self.dataset[self.t_name][0]

        x_range = slice(
            self.dataset[self.x_name].sel({self.x_name: numpy.min(point[0]) - 1}, method='bfill').values.item(),
            self.dataset[self.x_name].sel({self.x_name: numpy.max(point[0]) + 1}, method='ffill').values.item(),
        )
        y_range = slice(
            self.dataset[self.y_name].sel({
                self.y_name: numpy.min(point[1]) - 1,
            }, method='bfill').values.item(),
            self.dataset[self.y_name].sel({
                self.y_name: numpy.max(point[1]) + 1,
            }, method='ffill').values.item(),
        )
        time_range = slice(
            self.dataset['time'].sel(time=time, method='bfill').values,
            self.dataset['time'].sel(time=time, method='ffill').values,
        )

        if time_range.start == time_range.stop:
            time_range = time_range.start

        cell = self.dataset[variable].sel(
            {
                'time': time_range,
                self.x_name: x_range,
                self.y_name: y_range,
            }
        )

        if len(point.shape) > 1:
            cell = cell.interp({'time': time}) if 'time' in cell.dims else cell
            return xarray.concat(
                [
                    cell.interp({
                        self.x_name: location[0],
                        self.y_name: location[1],
                    })
                    for location in point.T
                ],
                dim='point',
            )
        else:
            cell = cell.interp({
                self.x_name: point[0],
                self.y_name: point[1],
            })
            return cell.interp({'time': time}) if 'time' in cell.dims else cell

    def u(self, point: numpy.array, time: datetime) -> float:
        return self._interpolate(self.u_name, point, time).values

    def v(self, point: numpy.array, time: datetime) -> float:
        return self._interpolate(self.v_name, point, time).values


class VectorGFS(VectorDataset):
    opendap_url = 'http://nomads.ncep.noaa.gov:80/dods/gfs_0p25_1hr/gfs20210413/gfs_0p25_1hr_12z'

    def __init__(self):
        dataset = xarray.open_dataset(self.opendap_url)

        super().__init__(
            dataset=dataset,
            u_name='ugrdprs',
            v_name='vgrdprs',
            z_name='lev',
        )
