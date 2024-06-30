import geopandas as gpd
import shapely
from shapely.geometry import Point, Polygon, box
import matplotlib.pyplot as plt
import numpy as np

import csv
import os


class Circle:
    """Represents generated circle"""
    def __init__(self, coordinates: list[float, float], radius: int, state=""):
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

        # Loading shapefiles of countries and converting them to EPSG:3857 - pseudo mercator coordinate system,
        # which is used in OpenStreetMap. Note: coordinates are represented in meters, not degrees.
        self.world = gpd.read_file('./data/world-administrative-boundaries/world-administrative-boundaries.shp').to_crs('EPSG:3857')  # Shapes of all countries
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

        max_radius_m = max_radius_km * 1000
        min_radius_m = min_radius_km * 1000

        # Generate circles
        def generate_circles_within_bbox(bbox: Polygon, max_radius_m) -> list:
            """
            Generates circles of maximum radius circle that fit the box of country shape entirely.
            :param bbox: bbox object with country shape
            :param max_radius_m: maximum radius of circle in meters
            :return:
            """
            x_min, y_min, x_max, y_max = bbox.bounds
            x_range = np.arange(x_min + max_radius_m, x_max, max_radius_m * 2)
            y_range = np.arange(y_min + max_radius_m, y_max, max_radius_m * 2)

            circles = []
            for x in x_range:
                for y in y_range:
                    circle = Point(x, y).buffer(max_radius_m)
                    if bbox.contains(circle):
                        circles.append(circle)
            return circles

        circles = generate_circles_within_bbox(bounding_box, max_radius_m)

        if self.verbose:
            print("Approximate circles generated, adjusting...")

        def filter_circles_within_polygon(circles, polygon: Polygon) -> list:
            """Filters circles that are fully within country shape"""
            filtered_circles = []
            for circle in circles:
                # First we check if circle is within a country shape.
                if polygon.contains(circle):
                    filtered_circles.append(circle)
                    circle_coordinates = [circle.centroid.x.item(), circle.centroid.y.item()]
                    circle_radius = max_radius_km * 1000
                    res_circle = Circle(circle_coordinates, round(circle_radius))
                    self.resulting_circles.append(res_circle)

                # If not, but circle is on the country border, we'll play with circle radius and position
                # to find one that fits. We will find neighbouring circles within country, then move our circle
                # in their direction, slightly reducing its radius until it fits.
                elif shapely.overlaps(circle, polygon):
                    x = circle.centroid.x
                    y = circle.centroid.y

                    # Find neighbours circle coordinates by generating them and filtering ones that are within country.
                    # Also store direction to that neighbour. It's coded for further simpler parsing in a following format:
                    # String of two characters +, - or 0. First character in a string represents x axis, second - y axis.
                    # + is increasing, - is decreasing, 0 is remaining the same. For example, "+0" means that x value is increased,
                    # y remains the same, therefore it's direction to the right.

                    top_neighbour = [Point(x, y + max_radius_m).buffer(max_radius_m), "0+"]
                    top_right_neighbour = [Point(x + max_radius_m, y + max_radius_m).buffer(max_radius_m), "++"]
                    right_neighbour = [Point(x + max_radius_m, y).buffer(max_radius_m), "+0"]
                    right_bottom_neighbour = [Point(x + max_radius_m, y - max_radius_m).buffer(max_radius_m), "+-"]
                    bottom_neighbour = [Point(x, y - max_radius_m).buffer(max_radius_m), "0-"]
                    bottom_left_neighbour = [Point(x - max_radius_m, y - max_radius_m).buffer(max_radius_m), "--"]
                    left_neighbour = [Point(x - max_radius_m, y).buffer(max_radius_m), "-0"]
                    left_top_neighbour = [Point(x - max_radius_m, y + max_radius_m).buffer(max_radius_m), "-+"]

                    neighbours = [top_neighbour, top_right_neighbour, right_neighbour,
                                  right_bottom_neighbour, bottom_neighbour, bottom_left_neighbour,
                                  left_neighbour, left_top_neighbour]

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
                        radius_m = max_radius_m - 1000
                        while overlaps and radius_m >= min_radius_m:
                            # Handle x coordinate
                            if direction[0] == "-":
                                x -= 1000
                            elif direction[0] == "+":
                                x += 1000

                            # Handle y coordinate
                            if direction[1] == "-":
                                y -= 1000
                            elif direction[1] == "+":
                                y += 1000

                            new_circle = Point(x, y).buffer(radius_m)

                            # If it fits, append it to the array of circles and exit loop
                            if polygon.contains(new_circle):
                                filtered_circles.append(new_circle)
                                res_circle = Circle([x.item(), y.item()], radius_m)
                                self.resulting_circles.append(res_circle)
                                overlaps = False
                            # Otherwise reduce radius by 1 km and start again
                            else:
                                radius_m = radius_m - 1000

            return filtered_circles

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
                radius = circle.radius
                circle_patch = plt.Circle(center, radius, edgecolor='red', facecolor='none')
                ax.add_patch(circle_patch)

        plt.title(f'Circles within {self.country_name}')
        plt.show()

    def save_csv(self, temp_dir=False) -> str:
        """Outputs result circles for country in CSV file format.
        Columns: state, x coordinate, y coordinate, radius.
        :param temp_dir: Save output file to temp dir instead of output_files root.
        :return: String with resulted file name
        """
        if temp_dir:
            dir_path = './output_files/temp'
        else:
            dir_path = './output_files'

        with open(f'{dir_path}/{self.country_name}.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)

            column_names = ['Region', 'X coordinate', 'Y coordinate', 'Radius']
            writer.writerow(column_names)

            data = []
            for circle in self.resulting_circles:
                # Converting meter-based coordinate system to latitude and longitude in degrees
                # and radius to kilometers.
                point = Point(circle.coordinates[0], circle.coordinates[1])
                gdf_proj = gpd.GeoDataFrame(geometry=[point], crs='EPSG:3857')
                gdf_epsg4326 = gdf_proj.to_crs('EPSG:4326')
                x_lon, y_lat = gdf_epsg4326.geometry.iloc[0].x, gdf_epsg4326.geometry.iloc[0].y

                data.append([circle.state, x_lon, y_lat, circle.radius / 1000])

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
