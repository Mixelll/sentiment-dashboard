from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS

import psycopg
from psycopg.rows import dict_row
import postgres_db as pgdb

# import os
# app.run(debug=os.getenv('FLASK_DEBUG', 'False') == 'True')


app = Flask(__name__)
CORS(app, origins=['http://localhost:4200'])


def validate_date(date_text):
    try:
        return datetime.strptime(date_text, '%Y-%m-%d')
    except ValueError:
        return None


@app.route('/api/sentiment', methods=['GET'])
def get_sentiment():
    ticker = request.args.get('ticker')
    start_date = validate_date(request.args.get('start_date'))
    end_date = validate_date(request.args.get('end_date'))
    relevance_threshold = float(request.args.get('relevance_score', default=0., type=float))

    if not ticker or not start_date or not end_date:
        return jsonify({'error': 'Missing parameters'}), 400

    try:
        data = pgdb.fetch_ticker_data(ticker, start_date, end_date, relevance_threshold)
        if not data:
            return jsonify({'error': 'No data found'}), 404
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
