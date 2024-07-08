import folium
import pandas as pd
import os
import webbrowser
from src.circles import CirclesGenerator


class Webmap:
    def show(self, country_names: list, min_r, max_r, world=False):
        """
        Renders circles given csv files using matplotlib
        :param country_names: List with names of countries to render
        :param min_r:
        :param max_r: min and max radius of circles to specify them in filename
        :return:
        """
        # Load dataframes
        dataframes = []

        for country in country_names:
            country_file_path = f'./output_files/{country}__{min_r}-{max_r}.csv'
            alt_country_file_path = f'./output_files/temp/{country}__{min_r}-{max_r}.csv'
            if os.path.exists(country_file_path):
                df = pd.read_csv(country_file_path)
            elif os.path.exists(alt_country_file_path):
                df = pd.read_csv(alt_country_file_path)

            # If there are no file with country name specified
            else:
                # Check, if this country exists at all
                from src.circles import CirclesGenerator
                cg = CirclesGenerator()
                if country not in cg.countries_list():
                    print(f'No country with name {country} found in files and dataset. Please check if you typed country name '
                          'correctly (you can use -l flag to list all country names)')
                else:
                    print(f'No file for {country} with circles from {min_r} to {max_r} found. '
                          f'Please generate it first by typing "python main.py -c {country}"')

                continue

            dataframes.append(df)

        if dataframes:
            merged_df = pd.concat(dataframes, ignore_index=True)

            # Convert columns to numeric and handle errors
            merged_df['X'] = pd.to_numeric(merged_df['Longitude'], errors='coerce')
            merged_df['Y'] = pd.to_numeric(merged_df['Latitude'], errors='coerce')
            merged_df['radius'] = pd.to_numeric(merged_df['Radius'], errors='coerce')

            # Drop rows with NaN values
            merged_df.dropna(subset=['X', 'Y', 'radius'], inplace=True)

            # Draw a map
            m = folium.Map(location=[merged_df['Y'].mean(), merged_df['X'].mean()], zoom_start=10)

            for _, row in merged_df.iterrows():
                folium.Circle(
                    location=[row['Y'], row['X']],
                    radius=row['radius'] * 1000,  # Folium radius should be set in meters, in CSV they are in kilometers
                    color='blue',
                    popup=f'Location: {row["Region"]}\nLat: {row["Y"]}\nLon: {row["X"]}\nRadius: {row["Radius"]}'
                ).add_to(m)

            if not world:
                output_file_path = f'./output_files/maps/{"__".join(country_names)}__{min_r}-{max_r}.html'
            else:
                output_file_path = f'./output_files/maps/world.html'
            m.save(output_file_path)
            print(f'HTML file with map was saved to {os.path.abspath(output_file_path)}')
            webbrowser.open('file://' + os.path.realpath(output_file_path))
