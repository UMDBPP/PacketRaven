from typing import List


class Point:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __eq__(self, other):
        return other.x == self.x and other.y == self.y

    def __str__(self):
        return f'POINT ({self.x} {self.y})'

    def __repr__(self):
        return str(self)


class PointSet:
    def __init__(self, points: List[Point]):
        self.points = points

    def convex_hull(self):
        # TODO implement convex hull
        pass

    def __str__(self):
        return str(self.points)

    def __repr__(self):
        return str(self)


class Line:
    def __init__(self, start: Point, end: Point):
        self.start = start
        self.end = end
        self.bounds = Bounds([self.start, self.end])
        self.m = (self.end.y - self.start.y) / (self.end.x - self.start.x)
        self.b = -1 * (self.m * self.start.x - self.start.y)

    def __contains__(self, point: Point):
        if point in self.bounds:
            return ((point.x - self.start.x) / (self.end.x - self.start.x)) == \
                   ((point.y - self.start.y) / (self.end.y - self.start.y))
        else:
            return False

    def __getitem__(self, x) -> float:
        return self.m * x + self.b

    def __str__(self):
        return f'LINESTRING ({self.start.x} {self.start.y}, {self.end.x} {self.end.y})'

    def __repr__(self):
        return str(self)


class Polyline:
    def __init__(self, points: List[Point]):
        self.points = points
        self.edges = []

        for point_index in range(len(self.points) - 1):
            current_point = self.points[point_index]
            next_point = self.points[point_index + 1]
            self.edges.append(Line(current_point, next_point))

    def __getitem__(self, index):
        return self.edges[index]

    def __str__(self):
        return f'LINESTRING (({", ".join([f"{point.x} {point.y}" for point in self.points])}))'

    def __repr__(self):
        return str(self)


class Bounds:
    def __init__(self, points: List[Point]):
        """
        Create rectangular bounds from a list of points.

        :param points: list of points
        """

        self.min_x = min([point.x for point in points])
        self.min_y = min([point.y for point in points])
        self.max_x = max([point.x for point in points])
        self.max_y = max([point.y for point in points])

    def __contains__(self, point: Point):
        return self.min_x <= point.x <= self.max_x and self.min_y <= point.y <= self.max_y

    def __str__(self):
        return f'({self.min_x}, {self.min_y}, {self.max_x}, {self.max_y})'

    def __repr__(self):
        return str(self)


class Polygon:
    def __init__(self, outer_points: List[Point], inner_points: List[Point] = None):
        """
        Build polygon from given vertices.

        :param outer_points: list of points on outer ring
        :param inner_points: list of points on inner ring
        """

        self.outer_points = outer_points
        self.inner_points = inner_points if inner_points is not None else []

        # TODO fix self-intersections
        self.outer_ring = []
        self.inner_ring = []

        for point_index in range(len(self.outer_points)):
            current_point = self.outer_points[point_index]

            if point_index < len(self.outer_points) - 1:
                next_point = self.outer_points[point_index + 1]
            else:
                next_point = self.outer_points[0]

            self.outer_ring.append(Line(current_point, next_point))

        if self.inner_points is not None:
            for point_index in range(len(self.inner_points)):
                current_point = self.inner_points[point_index]

                if point_index < len(self.inner_points) - 1:
                    next_point = self.inner_points[point_index + 1]
                else:
                    next_point = self.inner_points[0]

                self.inner_ring.append(Line(current_point, next_point))

        self.bounds = Bounds(self.outer_points + self.inner_points)

    def __contains__(self, point: Point):
        if point not in self.bounds:
            return False
        else:  # count the number of intersections between polygon edges and a horizontal ray originating from given point
            outer_intersections = 0

            for edge in self.outer_ring:
                if point in edge:
                    outer_intersections = 1
                    break
                # check if given point is left of the current edge (and lower than the highest vertex)
                elif (point in edge.bounds and point.x < ((point.y - edge.b) / edge.m)) or (
                        point.x < edge.bounds.max_x and edge.bounds.min_y <= point.y < edge.bounds.max_y):
                    outer_intersections += 1

            inner_intersections = 0

            for edge in self.inner_ring:
                if point in edge:
                    inner_intersections = 1
                    break
                # check if given point is left of the current edge (and lower than the highest vertex)
                elif (point in edge.bounds and point.x < ((point.y - edge.b) / edge.m)) or (
                        point.x < edge.bounds.max_x and edge.bounds.min_y <= point.y < edge.bounds.max_y):
                    inner_intersections += 1

            # the point is inside the polygon if the number of outer intersections is odd, and inner intersections even
            return outer_intersections % 2 != 0 and inner_intersections % 2 == 0

    def __str__(self):
        output = f'POLYGON (({", ".join([f"{point.x} {point.y}" for point in self.outer_points])})'

        if len(self.inner_points) > 0:
            output += f'({", ".join([f"{point.x} {point.y}" for point in self.inner_points])})'

        output += ')'
        return output

    def __repr__(self):
        return str(self)


def from_wkt(wkt: str):
    type, coords = wkt.split(' ', 1)

    if type.upper() == 'POLYGON':
        points = [[Point(*[float(entry) for entry in coord.split(' ')]) for coord in
                   ring_coords[1:-1].split(', ')] for ring_coords in coords[1:-1].split('), (')]

        if len(points) == 1:
            outer_points = points[0]
            inner_points = None
        else:
            outer_points, inner_points = points

        return Polygon(outer_points, inner_points)
    else:
        points = [Point(*[float(entry) for entry in coord.split(' ')]) for coord in
                  coords[1:-1].split(', ')]

        if type.upper() == 'POINT':
            return points[0]
        elif type.upper() == 'LINESTRING':
            return Polyline(points)


if __name__ == '__main__':
    polygon = from_wkt('POLYGON ((-2.12 0.49, -1.11 2.48, 1.33 2.31, 2.66 -0.06, 0.23 1.18, 1.05 -1.7, -1.45 -1.14))')
    points = [Point(-0.41, 1.81), Point(1.08, 0.41), Point(-1.6, -0.79), Point(1.24, -1.14)]

    for point in points:
        if point in polygon:
            print(f'{point} is inside {polygon}')
        else:
            print(f'{point} is outside {polygon}')
