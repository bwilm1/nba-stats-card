import time
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
from datetime import datetime, timedelta
from requests.exceptions import Timeout
import os
import json
from nba_api.stats.static import players
from nba_api.stats.endpoints import commonplayerinfo, playergamelog, leaguedashplayerstats
from nba_api.stats.library.parameters import SeasonAll

class NBAStatsCard:
    def __init__(self):
        self.colors = {
            'background': '#1E1E1E',
            'text': '#FFFFFF',
            'gradient_poor': '#FF4B4B',
            'gradient_neutral': '#808080',
            'gradient_excellent': '#4B9EFF'
        }
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'x-nba-stats-origin': 'stats',
            'x-nba-stats-token': 'true',
            'Referer': 'https://stats.nba.com/',
            'Connection': 'keep-alive',
        }
        self.cache_dir = 'cache'
        self.cache_duration = timedelta(hours=24)
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
    def _get_cache_path(self, player_name):
        """Get the cache file path for a player."""
        return os.path.join(self.cache_dir, f"{player_name.lower().replace(' ', '_')}_cache.json")
        
    def _load_from_cache(self, player_name):
        """Load player stats from cache if available and not expired."""
        cache_path = self._get_cache_path(player_name)
        if not os.path.exists(cache_path):
            return None
            
        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
                
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cache_time > self.cache_duration:
                return None
                
            return cache_data['stats']
        except:
            return None
            
    def _save_to_cache(self, player_name, stats):
        """Save player stats to cache."""
        cache_path = self._get_cache_path(player_name)
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'stats': stats
        }
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f)
        except:
            pass  # Ignore cache write errors
        
    def get_player_stats(self, player_name):
        """Get player stats from NBA.com API with retry logic and caching"""
        print(f"[DEBUG] Starting NBA stats lookup for {player_name}")
        
        # Try to load from cache first
        cached_stats = self._load_from_cache(player_name)
        if cached_stats:
            print("[DEBUG] Using cached stats")
            return cached_stats, []  # Return empty list for league stats since we don't cache those
            
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Find player ID
                player_dict = players.find_players_by_full_name(player_name)
                if not player_dict:
                    raise ValueError(f"Player {player_name} not found")
                
                player_id = player_dict[0]['id']
                print(f"[DEBUG] Found player ID: {player_id}")
                
                # Get player info with increased timeout and retry
                try:
                    player_info = commonplayerinfo.CommonPlayerInfo(
                        player_id=player_id,
                        timeout=30,  # Reduced timeout to prevent Gunicorn worker timeout
                        headers=self.headers
                    ).get_normalized_dict()
                except Timeout:
                    print(f"[DEBUG] Player info request timed out. Attempt {attempt + 1}/{max_retries}")
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(base_delay * (2 ** attempt))
                    continue
                
                # Get league stats with increased timeout and retry
                try:
                    player_stats = leaguedashplayerstats.LeagueDashPlayerStats(
                        season='2023-24',
                        headers=self.headers,
                        timeout=30,  # Reduced timeout to prevent Gunicorn worker timeout
                        per_mode_detailed='PerGame'
                    ).get_normalized_dict()
                except Timeout:
                    print(f"[DEBUG] League stats request timed out. Attempt {attempt + 1}/{max_retries}")
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(base_delay * (2 ** attempt))
                    continue
                
                # Find player's stats in league stats
                stats_list = player_stats['LeagueDashPlayerStats']
                player_current_stats = next(
                    (player for player in stats_list if player['PLAYER_ID'] == player_id),
                    None
                )
                
                if not player_current_stats:
                    raise ValueError("Could not find current season stats")
                
                # Combine info and stats
                stats = {
                    'name': player_info['CommonPlayerInfo'][0]['DISPLAY_FIRST_LAST'],
                    'team': f"{player_info['CommonPlayerInfo'][0]['TEAM_CITY']} {player_info['CommonPlayerInfo'][0]['TEAM_NAME']}",
                    'position': player_info['CommonPlayerInfo'][0]['POSITION'],
                    'G': player_current_stats['GP'],
                    'PTS': player_current_stats['PTS'],
                    'TRB': player_current_stats['REB'],
                    'AST': player_current_stats['AST'],
                    'FG%': player_current_stats['FG_PCT'],
                    '3P%': player_current_stats['FG3_PCT'],
                    'FT%': player_current_stats['FT_PCT'],
                    'PER': (player_current_stats['PTS'] + player_current_stats['REB'] + player_current_stats['AST']) / player_current_stats['GP'],  # Simple approximation
                    'TS%': (player_current_stats['PTS'] / (2 * (player_current_stats['FGA'] + 0.44 * player_current_stats['FTA']))) if player_current_stats['FGA'] > 0 else 0,
                    'AST/G': player_current_stats['AST'] / player_current_stats['GP'],
                    'TRB/G': player_current_stats['REB'] / player_current_stats['GP']
                }
                
                # Save to cache
                self._save_to_cache(player_name, stats)
                
                print("[DEBUG] Successfully retrieved player stats")
                return stats, stats_list
                
            except Timeout:
                wait_time = base_delay * (2 ** attempt)
                print(f"[DEBUG] Timeout occurred. Attempt {attempt + 1}/{max_retries}. Waiting {wait_time} seconds...")
                if attempt == max_retries - 1:
                    raise Exception("NBA API timed out after multiple attempts. Please try again later.")
                time.sleep(wait_time)
                continue
                
            except Exception as e:
                print(f"[ERROR] Failed to fetch stats: {str(e)}")
                raise

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
        # Get player stats
        stats, league_stats = self.get_player_stats(player_name)
        
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
        draw.text((40, 40), stats['name'], fill=self.colors['text'], font=title_font)
        draw.text((40, 100), f"{stats['team']} | {stats['position']}", 
                 fill=self.colors['text'], font=header_font)

        # Draw basic stats
        y_pos = 180
        basic_stats = [
            f"Games Played: {stats['G']}",
            f"Points: {stats['PTS']:.1f}",
            f"Rebounds: {stats['TRB']:.1f}",
            f"Assists: {stats['AST']:.1f}",
            f"FG%: {stats['FG%']:.1%}",
            f"3P%: {stats['3P%']:.1%}",
            f"FT%: {stats['FT%']:.1%}"
        ]

        for stat in basic_stats:
            draw.text((40, y_pos), stat, fill=self.colors['text'], font=stats_font)
            y_pos += 40

        # Draw advanced stats with percentiles
        y_pos += 40
        draw.text((40, y_pos), "Advanced Stats (with League Percentile)", 
                 fill=self.colors['text'], font=header_font)
        y_pos += 50

        # Calculate and display advanced stats percentiles
        advanced_stats = {
            'PER': [stats['PER'], [(p['PTS'] + p['REB'] + p['AST']) / p['GP'] for p in league_stats]],
            'TS%': [stats['TS%'] * 100, [(p['PTS'] / (2 * (p['FGA'] + 0.44 * p['FTA']))) * 100 if p['FGA'] > 0 else 0 for p in league_stats]],
            'AST/G': [stats['AST/G'], [p['AST'] / p['GP'] for p in league_stats]],
            'REB/G': [stats['TRB/G'], [p['REB'] / p['GP'] for p in league_stats]]
        }

        for stat_name, (stat_value, league_values) in advanced_stats.items():
            if pd.notna(stat_value):  # Only display if value exists
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
                 "Data via NBA.com Stats",
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
