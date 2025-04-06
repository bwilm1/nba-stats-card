# NBA Stats Card Generator

A Python script that generates visually appealing NBA player stats cards inspired by JFresh's NHL cards. The cards display both basic and advanced statistics with gradient-colored performance indicators.

## Features

- Player basic information (name, team, position)
- Current season statistics
- Advanced metrics with percentile rankings
- Visual gradient indicators (red to blue) for performance
- Automated data fetching from NBA.com Stats

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

## Web Application

To run the web application locally:
```bash
python app.py
```

Then open your browser and navigate to http://127.0.0.1:5000/

## Deployment

This application is configured for deployment on platforms like Render, Heroku, or PythonAnywhere.

### Render Deployment

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set the build command: `pip install -r requirements.txt`
4. Set the start command: `gunicorn app:app`
5. Deploy!

### Heroku Deployment

1. Create a new Heroku app
2. Connect your GitHub repository
3. Deploy!

## Output

The script generates a PNG image file containing the player's stats card.

## Data Sources

All data is fetched from NBA.com Stats API.

## Note

This is a basic implementation that can be extended with:
- Command-line arguments for player selection
- Additional advanced statistics
- Custom team color schemes
- Player headshots and team logos
- Interactive web interface
