import geopandas as gpd
import shapely
from shapely.geometry import Point, Polygon, box
from shapely.affinity import scale
import matplotlib.pyplot as plt
import numpy as np

import csv
import os


class Circle:
    """Represents generated circle"""
    def __init__(self, country_name: str, coordinates: list[float, float], radius: int, state=""):
        self.country = country_name
        self.state = state
        self.coordinates = coordinates
        self.radius = radius


class CirclesGenerator:
    def __init__(self, verbose=False):
        self.country_name = None
        self.bounding_box = None  # Box, in which country shape fits in
        self.polygon = None  # Placeholder for shape of a country
        self.filtered_circles = []  # Placeholder for circles within country shape in shape format
        self.resulting_circles = []  # Placeholder for circles in output format - [[x, y], radius]
        self.world = gpd.read_file('./data/world-administrative-boundaries/world-administrative-boundaries.shp')  # Shapes of all countries
        self.states = gpd.read_file('./data/ne_10m_admin_1_states_provinces/ne_10m_admin_1_states_provinces.shp')  # Shapes of all states in countries

        self.verbose = verbose

    def generate_circles(self, country_name, min_circle_radius, max_circle_radius, as_shapes=False) -> list | str:
        """
        Generates circles set for given country.
        :param country_name: Country name to generate circles to
        :param min_circle_radius: Minimal radius for a circle, in kilometers
        :param max_circle_radius: Max radius for a circle, in kilometers
        :param as_shapes: If true, returns circles shapes instead of coordinates and radius
        :return: List of
        """
        self.country_name = country_name
        country = self.world.loc[self.world['name'] == country_name]

        if country.empty:
            return "Country not found in the dataset"

        polygon = country.geometry.iloc[0]
        self.polygon = polygon
        minx, miny, maxx, maxy = polygon.bounds
        bounding_box = box(minx, miny, maxx, maxy)
        self.bounding_box = bounding_box

        if self.verbose:
            print("Map data loaded...")

        # Define circles parameters
        min_radius_km = min_circle_radius
        max_radius_km = max_circle_radius

        max_radius_deg = max_radius_km / 111  # Approximate conversion: 1 degree ~ 111 km
        min_radius_deg = min_radius_km / 111

        # Generate circles
        def generate_circles_within_bbox(bbox: Polygon, radius_deg) -> list:
            """
            Generates circles of maximum radius circle that fit the box of country shape entirely
            :param bbox: bbox object with country shape
            :param radius_deg: radius of circle in degrees (km divided by 111)
            :return:
            """
            x_min, y_min, x_max, y_max = bbox.bounds
            y_range = np.arange(y_min + radius_deg, y_max, radius_deg * 2)

            circles = []

            for y in y_range:
                # Adjust the x-range based on the latitude to maintain consistent distances in kilometers
                x_scale_fact = np.cos(np.radians(y))
                radius_deg_lon = radius_deg / x_scale_fact
                x_range = np.arange(x_min + radius_deg_lon, x_max, radius_deg_lon * 2)
                for x in x_range:
                    circle = Point(x, y).buffer(radius_deg)
                    oval = scale(circle, xfact=(1/x_scale_fact), yfact=1)
                    if bbox.contains(oval):
                        circles.append(oval)

            return circles

        circles = generate_circles_within_bbox(bounding_box, max_radius_deg)

        if self.verbose:
            print("Approximate circles generated, adjusting...")

        def filter_circles_within_polygon(circles, polygon: Polygon, second_try=False) -> list:
            """Filters circles that are fully within country shape"""
            filtered_circles = []
            for circle in circles:
                # First we check if circle is within a country shape.
                if polygon.contains(circle):
                    filtered_circles.append(circle)
                    circle_coordinates = [round(circle.centroid.x.item(), 7), round(circle.centroid.y.item(), 7)]
                    y_min, y_max = circle.bounds[1], circle.bounds[3]
                    circle_radius = max_circle_radius if not second_try else min_circle_radius
                    res_circle = Circle(country_name, circle_coordinates, round(circle_radius))
                    self.resulting_circles.append(res_circle)

                # If not, but circle is on the country border, we'll play with circle radius and position
                # to find one that fits. We will find neighbouring circles within country, then move our circle
                # in their direction, slightly reducing it's radius until it fits.
                elif shapely.overlaps(circle, polygon):
                    x = circle.centroid.x
                    y = circle.centroid.y

                    x_scale_fact = np.cos(np.radians(y))
                    x_max_radius_deg = max_radius_deg / x_scale_fact  # Adjusting scales for x coordinate

                    # Find neighbours circle coordinates by generating them and filtering ones that are within country.
                    # Also store direction to that neighbour. It's coded for further simpler parsing in a following format:
                    # String of two characters +, - or 0. First character in a string represents x axis, second - y axis.
                    # + is increasing, - is decreasing, 0 is remaining the same. For example, "+0" means that x value is increased,
                    # y remains the same, therefore it's direction to the right.

                    top_neighbour = [Point(x, y + max_radius_deg).buffer(max_radius_deg), "0+"]
                    top_right_neighbour = [Point(x + x_max_radius_deg, y + max_radius_deg).buffer(max_radius_deg), "++"]
                    right_neighbour = [Point(x + x_max_radius_deg, y).buffer(max_radius_deg), "+0"]
                    right_bottom_neighbour = [Point(x + x_max_radius_deg, y - max_radius_deg).buffer(max_radius_deg), "+-"]
                    bottom_neighbour = [Point(x, y - max_radius_deg).buffer(max_radius_deg), "0-"]
                    bottom_left_neighbour = [Point(x - x_max_radius_deg, y - max_radius_deg).buffer(max_radius_deg), "--"]
                    left_neighbour = [Point(x - x_max_radius_deg, y).buffer(max_radius_deg), "-0"]
                    left_top_neighbour = [Point(x - x_max_radius_deg, y + max_radius_deg).buffer(max_radius_deg), "-+"]

                    neighbours = [top_neighbour, top_right_neighbour, right_neighbour,
                                  right_bottom_neighbour, bottom_neighbour, bottom_left_neighbour,
                                  left_neighbour, left_top_neighbour]

                    for n in neighbours:
                        n[0] = scale(n[0], xfact=np.cos(np.radians(y)), yfact=1)

                    filtered_neighbours = [neighbour for neighbour in neighbours if polygon.contains(neighbour[0])]

                    # First we check if there are only one neighbour - in that case direction will be equal to direction
                    # of that neighbour from our circle point of view.
                    if len(filtered_neighbours) == 1:
                        direction = filtered_neighbours[0][1]

                    elif len(filtered_neighbours) == 0:
                        direction = None

                    # If there are more than one neighbour, we calculate directions by adding them.
                    else:
                        # Extract only neighbours that are place not diagonally, because we don't want to count them
                        non_diagonal_neighobours = [d[1] for d in filtered_neighbours if "0" in d[1]]

                        # Add directions of remaining neighbours to find direction we need to move our circle
                        _x = 0
                        _y = 0
                        for d in non_diagonal_neighobours:
                            if d[0] == "-":
                                _x -= 1
                            elif d[0] == "+":
                                _x += 1

                            if d[1] == "-":
                                _y -= 1
                            elif d[1] == "+":
                                _y += 1

                        direction_mapping = {
                            1: "+",
                            0: "0",
                            -1: "-"
                        }

                        direction = f'{direction_mapping.get(_x)}{direction_mapping.get(_y)}'

                    # Now when we have direction to move our circle, we will move it there decreasing it's radius by 1 km
                    # until it will not overlap with border.
                    if direction:
                        overlaps = True
                        radius_deg = (max_radius_km - 1) / 111
                        while overlaps and radius_deg >= min_radius_deg:
                            # Handle x coordinate
                            if direction[0] == "-":
                                x -= (1 / 111) / np.cos(np.radians(y))
                            elif direction[0] == "+":
                                x += (1 / 111) / np.cos(np.radians(y))

                            # Handle y coordinate
                            if direction[1] == "-":
                                y -= 1 / 111
                            elif direction[1] == "+":
                                y += 1 / 111

                            new_circle = Point(x, y).buffer(radius_deg)
                            new_oval = scale(new_circle, xfact=1/x_scale_fact, yfact=1)

                            # If it fits, append it to the array of circles and exit loop
                            if polygon.contains(new_oval):
                                filtered_circles.append(new_oval)
                                res_circle = Circle(country_name, [round(x.item(), 7), round(y.item(), 7)], round(radius_deg * 111))
                                self.resulting_circles.append(res_circle)
                                overlaps = False
                            # Otherwise reduce radius by 1 km and start again
                            else:
                                radius_deg = radius_deg - 1 / 111

            if filtered_circles:
                return filtered_circles
            elif not second_try:
                # If country to small and 10km circles didn't fit in, call function again with 1 km circles
                small_circles = generate_circles_within_bbox(self.bounding_box, min_radius_deg)
                return filter_circles_within_polygon(small_circles, polygon, second_try=True)

        filtered_circles = filter_circles_within_polygon(circles, polygon)
        self.filtered_circles = filtered_circles

        if self.verbose:
            print("Circles on borders adjusted...")
            print(f'Total {len(self.resulting_circles)} circles generated')

        if as_shapes:
            return filtered_circles

        return self.resulting_circles

    def add_areas_names(self):
        """
        Adds to each circle name of a state/region where it's located
        :return:
        """
        for circle in self.resulting_circles:
            circle_center = Point(circle.coordinates[0], circle.coordinates[1])
            state_obj = self.states[self.states.contains(circle_center)]
            state_obj.to_crs('EPSG:3857')

            if not state_obj.empty:
                circle.state = state_obj.iloc[0]["name_en"]

        if self.verbose:
            print("Circle state names parsed...")


    def visualize(self, as_shapes=False, via_matplotlib=False):
        """Render result of generated circles in matplotlib"""
        if self.verbose:
            print("Rendering...")
        fig, ax = plt.subplots(figsize=(10, 10))
        gpd.GeoSeries([self.bounding_box]).plot(ax=ax, edgecolor='black', facecolor='none')
        gpd.GeoSeries([self.polygon]).plot(ax=ax, edgecolor='blue', facecolor='none')

        if as_shapes:
            for circle in self.filtered_circles:
                gpd.GeoSeries([circle]).plot(ax=ax, edgecolor='red', facecolor='none')
        else:
            for circle in self.resulting_circles:
                center = circle.coordinates
                radius = circle.radius / 111
                circle_patch = plt.Circle(center, radius, edgecolor='red', facecolor='none')
                ax.add_patch(circle_patch)

        plt.title(f'Circles within {self.country_name}')
        plt.show()

    def save_csv(self, min_r, max_r, temp_dir=False) -> str:
        """Outputs result circles for country in CSV file format.
        Columns: state, x coordinate, y coordinate, radius.
        :param temp_dir: Save output file to temp dir instead of output_files root.
        :param min_r:
        :param max_r: Min and max radius of circles to mark them in filename
        :return: String with resulted file name
        """
        if temp_dir:
            dir_path = './output_files/temp'
        else:
            dir_path = './output_files'

        with open(f'{dir_path}/{self.country_name}__{min_r}-{max_r}.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)

            column_names = ['Region', 'X coordinate', 'Y coordinate', 'Radius']
            writer.writerow(column_names)

            data = []
            for circle in self.resulting_circles:
                data.append([f'{circle.country}_{circle.state}', circle.coordinates[0], circle.coordinates[1], circle.radius])

            writer.writerows(data)

        return os.path.abspath(f'./output_files/{self.country_name}.csv')

    def countries_list(self):
        """Returns list with all countries names"""
        countries = []
        if self.verbose:
            print("Getting list of all country names...")
        for index, country in self.world.iterrows():
            countries.append(country['name'])

        return countries
