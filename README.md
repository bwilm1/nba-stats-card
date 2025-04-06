# NBA Stats Card Generator

A Python script that generates visually appealing NBA player stats cards inspired by JFresh's NHL cards. The cards display both basic and advanced statistics with gradient-colored performance indicators.

## Features

- Player basic information (name, team, position)
- Current season statistics
- Advanced metrics with percentile rankings
- Visual gradient indicators (red to blue) for performance
- Automated data fetching from Basketball-Reference

## Requirements

- Python 3.8+
- Required packages listed in `requirements.txt`

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the script with:
```bash
python nba_card_generator.py
```

By default, it will generate a stats card for LeBron James. To modify for a different player, edit the `main()` function in `nba_card_generator.py`.

## Output

The script generates a PNG image file named `nba_stats_card.png` containing the player's stats card.

## Data Sources

All data is fetched from Basketball-Reference, a comprehensive basketball statistics website.

## Note

This is a basic implementation that can be extended with:
- Command-line arguments for player selection
- Additional advanced statistics
- Custom team color schemes
- Player headshots and team logos
- Interactive web interface
