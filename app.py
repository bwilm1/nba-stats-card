from flask import Flask, render_template, request, send_from_directory
import os
from nba_card_generator import NBAStatsCard

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
            return render_template('index.html', filename=filename)
        except Exception as e:
            app.logger.error(f'Error generating card: {str(e)}')
            return f"Error: {str(e)}", 500
    return render_template('index.html')

@app.route('/cards/<filename>')
def serve_card(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
