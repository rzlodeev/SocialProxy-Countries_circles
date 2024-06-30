import argparse
import os
import pandas as pd

from src.circles import CirclesGenerator
from src.map import Webmap


def main():
    # Define parser for launching script from bash with arguments
    parser = argparse.ArgumentParser(description="This script generates list of circles of given radius range "
                                                 "that cover given country. \n"
                                                 "Usage: ")

    country_or_world_group = parser.add_mutually_exclusive_group()
    country_or_world_group.add_argument('-c', '--country-name', type=str, nargs='+', help='Name of a country you want to get circles for.')
    country_or_world_group.add_argument('-w', '--world', action='store_true', help='Get countries for all countries in the world.')
    parser.add_argument('-mn', '--min-radius', type=int, help='Min radius of resulting circles in kilometers. Defaults to 1.', default=1)
    parser.add_argument('-mx', '--max-radius', type=int, help='Max radius of resulting circles in kilometers. Defaults to 10.', default=10)
    parser.add_argument('-m', '--visualize', action='store_true', help='Visualize result using matplotlib.')
    parser.add_argument('-l', '--list-countries', action='store_true', help='List all available countries names')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose mode. Keeps you in touch with program progress.')
    parser.add_argument('-o', '--overwrite-files', action='store_true', help='Overwrite existing files in temp directory when processing the whole world.')
    parser.add_argument('-f', '--from-file', type=str, nargs='+', help='Visualize country csv files.')
    args = parser.parse_args()

    # Generate circles itself
    circles_generator = CirclesGenerator(verbose=args.verbose)

    # List country names if needed (-l flag)
    if args.list_countries:
        countries_list = circles_generator.countries_list()
        print(f'List of {len(countries_list)} countries:')
        for t in countries_list:
            print(t)

    # When country name given (-c flag)
    if args.country_name:
        for country_name_str in args.country_name:
            circles_status = circles_generator.generate_circles(country_name_str, args.min_radius, args.max_radius)
            if type(circles_status) == str:
                print(circles_status)
            else:
                circles_generator.add_areas_names()
                file_name = circles_generator.save_csv(min_r=args.min_radius, max_r=args.max_radius)
                print(f'CSV file was saved to {file_name}')
        if args.visualize:
            webmap = Webmap()
            webmap.show(args.country_name, args.min_radius, args.max_radius)

    elif args.world:  # -w flag
        generate_world(args)

    if args.from_file:

        webmap = Webmap()
        webmap.show(args.from_file, min_r=args.min_radius, max_r=args.max_radius)


def generate_world(args):
    """Generates circles for every country in a world"""

    # Get world map dataset
    circles_generator = CirclesGenerator(verbose=args.verbose)
    world = circles_generator.world
    country_names = []  # Placeholder for processed country names to exclude re-running the same country twice
    csvs_dir = './output_files/temp'

    # Iterate to get each country, save it to csv and merge csv into one big file
    for index, country in world.iterrows():
        country_name = country['name']
        if country_name not in country_names:
            country_names.append(country_name)
            if args.overwrite_files or f'{country_name}__{args.min_radius}-{args.max_radius}.csv' not in os.listdir(csvs_dir):
                print(f'Processing {country_name}...')
                circles_generator.generate_circles(country_name, args.min_radius, args.max_radius)
                circles_generator.add_areas_names()
                circles_generator.save_csv(temp_dir=True, min_r=args.min_radius, max_r=args.max_radius)
            else:
                print(f'{country_name} loaded from previous existing CSV file')

    dfs = []  # Dataframes placeholder

    # Merging resulted csvs in one file
    for filename in os.listdir(csvs_dir):
        if filename.endswith(".csv"):
            file_path = os.path.join(csvs_dir, filename)
            df = pd.read_csv(file_path)
            dfs.append(df)

    merged_df = pd.concat(dfs, ignore_index=True)
    output_path = f'./output_files/1world__{args.min_radius}-{args.max_radius}.csv'
    merged_df.to_csv(output_path, index=False)
    print('World processing finished.')


if __name__ == '__main__':
    main()

