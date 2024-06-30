# Countries circles

## Description
This script generates circles with given min and max radius for given country, and saves resulting circles coordinates
and radius in CSV file(s).

## Installation

### Prequisites
    Python (3.11 or higher)
    Git

### Clone the repository
Clone the repository to your local machine using:

```bash
git clone https://github.com/rzlodeev/SocialProxy-Countries_circles.git
cd SocialProxy-Countries_circles
```

### Setup virtual environment
Create and activate virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```


### Install the necessary packages using pip:

```bash
pip install -r requirements.txt
```

## Usage

To run the script:
```bash
python main.py --arguments
```

### Common use-cases:

Get CSV file for specified country:
> Make sure you first letter of country name is capital. You can check available country names using -l argument
```bash
python main.py -c Italy
```

Countries with several words in the name are typed with brackets. Note that each word also starts with a capital.
You can also call several countries at once.
```bash
python main.py -c Italy 'Saudi Arabia' -v

Get CSV file for all countries in a world:
```bash
python main.py -w
```

Visualize result:
```bash
python main.py -c Italy -m
```

Render and open map for pre-made csv file:
```bash
python main.py -f Italy
```

Each csv and html map file follows this name structure:

`country name(-s), two underscores, min circle radius, dash, max circle radius.`


### Arguments definition
| Argument | Short Form | Type | Description | Default |
|----------|-------------|------|-------------|---------|
| `--country-name` | `-c` | `str`, `nargs='+'` | Name of a country you want to get circles for. | N/A (required) |
| `--world` | `-w` | `store_true` | Get countries for all countries in the world. | N/A (required) |
| `--min-radius` | `-mn` | `int` | Min radius of resulting circles in kilometers. | 1 |
| `--max-radius` | `-mx` | `int` | Max radius of resulting circles in kilometers. | 10 |
| `--visualize` | `-m` | `store_true` | Visualize result using matplotlib. | False |
| `--list-countries` | `-l` | `store_true` | List all available countries names. | False |
| `--verbose` | `-v` | `store_true` | Verbose mode. Keeps you in touch with program progress. | False |
| `--overwrite-files` | `-o` | `store_true`| Overwrite existing files in temp directory when processing the whole world. | False |

