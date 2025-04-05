import time
from nba_api.stats.static import players
from nba_api.stats.endpoints import commonplayerinfo, playergamelog, leaguedashplayerstats
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from datetime import datetime
from requests.exceptions import Timeout

class NBAStatsCard:
    def __init__(self):
        self.colors = {
            'background': '#1E1E1E',
            'text': '#FFFFFF',
            'gradient_poor': '#FF4B4B',
            'gradient_neutral': '#808080',
            'gradient_excellent': '#4B9EFF'
        }
        
    def get_player_info(self, player_name):
        """Get basic player information."""
        player_dict = players.find_players_by_full_name(player_name)
        if not player_dict:
            raise ValueError(f"Player {player_name} not found")
        
        player_id = player_dict[0]['id']
        player_info = commonplayerinfo.CommonPlayerInfo(player_id=player_id).get_normalized_dict()
        return player_info['CommonPlayerInfo'][0]

    def get_player_stats(self, player_id):
        """Get current season stats for player with retry logic."""
        max_retries = 3
        base_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                league_stats = leaguedashplayerstats.LeagueDashPlayerStats(
                    season='2023-24',
                    per_mode_detailed='PerGame',
                    timeout=60
                ).get_normalized_dict()
                
                player_stats = None
                for player in league_stats['LeagueDashPlayerStats']:
                    if player['PLAYER_ID'] == player_id:
                        player_stats = player
                        break
                        
                if not player_stats:
                    raise ValueError(f"Could not find stats for player ID {player_id}")
                    
                return player_stats, league_stats['LeagueDashPlayerStats']
                
            except Timeout:
                if attempt == max_retries - 1:
                    raise Exception("NBA API timed out after multiple attempts. Please try again later.")
                time.sleep(base_delay * (2 ** attempt))  # Exponential backoff
                continue
                
            except Exception as e:
                raise Exception(f"Error fetching player stats: {str(e)}")

    def calculate_percentile(self, value, stat_list):
        """Calculate percentile rank for a given stat."""
        return round(sum(1 for x in stat_list if x <= value) / len(stat_list) * 100)

    def get_gradient_color(self, percentile):
        """Get color based on percentile rank."""
        if percentile < 50:
            # Poor to neutral
            ratio = percentile / 50
            r = int(int(self.colors['gradient_poor'][1:3], 16) * (1 - ratio) + 
                   int(self.colors['gradient_neutral'][1:3], 16) * ratio)
            g = int(int(self.colors['gradient_poor'][3:5], 16) * (1 - ratio) + 
                   int(self.colors['gradient_neutral'][3:5], 16) * ratio)
            b = int(int(self.colors['gradient_poor'][5:7], 16) * (1 - ratio) + 
                   int(self.colors['gradient_neutral'][5:7], 16) * ratio)
        else:
            # Neutral to excellent
            ratio = (percentile - 50) / 50
            r = int(int(self.colors['gradient_neutral'][1:3], 16) * (1 - ratio) + 
                   int(self.colors['gradient_excellent'][1:3], 16) * ratio)
            g = int(int(self.colors['gradient_neutral'][3:5], 16) * (1 - ratio) + 
                   int(self.colors['gradient_excellent'][3:5], 16) * ratio)
            b = int(int(self.colors['gradient_neutral'][5:7], 16) * (1 - ratio) + 
                   int(self.colors['gradient_excellent'][5:7], 16) * ratio)
        return f'#{r:02x}{g:02x}{b:02x}'

    def create_stats_card(self, player_name):
        """Generate the stats card for a given player."""
        # Get player info and stats
        player_info = self.get_player_info(player_name)
        player_stats, league_stats = self.get_player_stats(player_info['PERSON_ID'])
        
        # Create image
        width, height = 800, 1000
        image = Image.new('RGB', (width, height), self.colors['background'])
        draw = ImageDraw.Draw(image)
        
        # Load fonts (you'll need to provide your own font files)
        try:
            title_font = ImageFont.truetype("arial.ttf", 40)
            header_font = ImageFont.truetype("arial.ttf", 30)
            stats_font = ImageFont.truetype("arial.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            stats_font = ImageFont.load_default()

        # Draw player name and basic info
        draw.text((40, 40), f"{player_info['DISPLAY_FIRST_LAST']}", 
                 fill=self.colors['text'], font=title_font)
        draw.text((40, 100), 
                 f"{player_info['TEAM_CITY']} {player_info['TEAM_NAME']} | {player_info['POSITION']}",
                 fill=self.colors['text'], font=header_font)

        # Draw basic stats
        y_pos = 180
        basic_stats = [
            f"Games Played: {player_stats['GP']}",
            f"Points: {player_stats['PTS']:.1f}",
            f"Rebounds: {player_stats['REB']:.1f}",
            f"Assists: {player_stats['AST']:.1f}",
            f"FG%: {player_stats['FG_PCT']:.1%}",
            f"3P%: {player_stats['FG3_PCT']:.1%}",
            f"FT%: {player_stats['FT_PCT']:.1%}"
        ]

        for stat in basic_stats:
            draw.text((40, y_pos), stat, fill=self.colors['text'], font=stats_font)
            y_pos += 40

        # Draw advanced stats with percentiles
        y_pos += 40
        draw.text((40, y_pos), "Advanced Stats", fill=self.colors['text'], font=header_font)
        y_pos += 50

        # Calculate and display advanced stats percentiles
        advanced_stats = {
            'PER': [player_stats['PTS'] / player_stats['MIN'] * 36, [p['PTS'] / p['MIN'] * 36 for p in league_stats if p['MIN'] > 0]],  # Using points per 36 as a simple substitute
            'TS%': [player_stats['FG_PCT'] * 100, [p['FG_PCT'] * 100 for p in league_stats]],  # Using FG% as a simpler substitute
            'AST': [player_stats['AST'] / player_stats['MIN'] * 36, [p['AST'] / p['MIN'] * 36 for p in league_stats if p['MIN'] > 0]],  # Assists per 36 minutes
            'REB': [player_stats['REB'] / player_stats['MIN'] * 36, [p['REB'] / p['MIN'] * 36 for p in league_stats if p['MIN'] > 0]]  # Rebounds per 36 minutes
        }

        for stat_name, (stat_value, league_values) in advanced_stats.items():
            percentile = self.calculate_percentile(stat_value, league_values)
            color = self.get_gradient_color(percentile)
            
            # Draw stat background
            draw.rectangle([35, y_pos-5, 400, y_pos+35], fill=color)
            draw.text((40, y_pos), 
                     f"{stat_name}: {stat_value:.1f} ({percentile}th percentile)", 
                     fill=self.colors['text'], font=stats_font)
            y_pos += 50

        # Add footer
        draw.text((40, height-60), 
                 f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                 fill=self.colors['text'], font=stats_font)
        draw.text((40, height-30), 
                 "Data via nba_api",
                 fill=self.colors['text'], font=stats_font)

        return image

def main():
    import sys
    import os

    # Create cards directory if it doesn't exist
    cards_dir = "cards"
    if not os.path.exists(cards_dir):
        os.makedirs(cards_dir)
        
    if len(sys.argv) > 1:
        player_name = ' '.join(sys.argv[1:])
    else:
        player_name = "LeBron James"  # Default player
        
    generator = NBAStatsCard()
    try:
        print(f"Generating stats card for {player_name}...")
        card = generator.create_stats_card(player_name)
        output_file = os.path.join(cards_dir, f"{player_name.replace(' ', '_').lower()}_stats_card.png")
        card.save(output_file)
        print(f"Stats card generated successfully! Saved as: {output_file}")
    except Exception as e:
        print(f"Error generating stats card: {str(e)}")

if __name__ == "__main__":
    main()
