from flask import Flask, render_template, request, send_from_directory
import os
from nba_card_generator import NBAStatsCard

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'cards'

# Ensure cards directory exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

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
            return render_template('index.html', card_generated=True, filename=filename)
        except Exception as e:
            return render_template('index.html', error=str(e))
    return render_template('index.html')

@app.route('/cards/<filename>')
def serve_card(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
