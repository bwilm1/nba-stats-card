from flask import Flask, render_template, request, send_from_directory
import os
from nba_card_generator import NBAStatsCard
from requests.exceptions import Timeout

app = Flask(__name__)

# Ensure cards directory exists
cards_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cards')
if not os.path.exists(cards_dir):
    os.makedirs(cards_dir)
app.config['UPLOAD_FOLDER'] = cards_dir

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        player_name = request.form['player_name']
        generator = NBAStatsCard()
        try:
            card = generator.create_stats_card(player_name)
            filename = f"{player_name.replace(' ', '_').lower()}_stats_card.png"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            card.save(filepath)
            return render_template('index.html', filename=filename, card_generated=True)
        except Timeout:
            error_msg = "Basketball-Reference is currently unavailable. Please try again later."
            app.logger.error(f'Basketball-Reference timeout for player: {player_name}')
            return render_template('index.html', error=error_msg)
        except ValueError as e:
            if "Player not found" in str(e):
                return render_template('index.html', error=f"Player '{player_name}' not found. Please check the spelling.")
            return render_template('index.html', error=str(e))
        except Exception as e:
            app.logger.error(f'Error generating card for {player_name}: {str(e)}')
            return render_template('index.html', error="An unexpected error occurred. Please try again.")
    return render_template('index.html')

@app.route('/cards/<filename>')
def serve_card(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# This is only used when running locally. On production, WSGI is configured differently
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
