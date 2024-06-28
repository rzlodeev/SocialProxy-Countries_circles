import argparse

from src.circles import CirclesGenerator

def main():
    # Define parser for launching script from bash with arguments
    parser = argparse.ArgumentParser(description="This script generates list of circles of given radius range "
                                                 "that cover given country. \n"
                                                 "Usage: ")

    country_or_world_group = parser.add_mutually_exclusive_group(required=True)
    country_or_world_group.add_argument('-c', 'country-name', type=str, nargs='+', help='Name of a country you want to get circles for.')
    country_or_world_group.add_argument('-w', '--world', action='store_true', help='Get countries for all countries in the world.')
    parser.add_argument('-mn', '--min-radius', type=int, help='Min radius of resulting circles in kilometers. Defaults to 1.', default=1)
    parser.add_argument('-mx', '--max-radius', type=int, help='Max radius of resulting circles in kilometers. Defaults to 10.', default=10)
    parser.add_argument('-l', '--visualize', action='store_true', help='Visualize result using matplotlib.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose mode. Keeps you in touch with program progress.')
    args = parser.parse_args()

    # Generate circles itself
    circles_generator = CirclesGenerator(verbose=args.verbose)

    # When country name given
    if args.country_name:
        circles_generator.generate_circles(args.country_name, args.min_radius, args.max_radius)
        circles_generator.add_areas_names()
        circles_generator.save_csv()
        if args.visualize:
            circles_generator.visualize()
    elif args.world:
        #TODO: Add world case handling; add usage in bash; write usage in readme.md
        pass


if __name__ == '__main__':
    main()

