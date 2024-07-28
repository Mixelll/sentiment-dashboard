import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS
import psycopg
import postgres_db as pgdb
import os

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:4200", "http://michaelleitsin.com"]}})


# Configure logging
logging.basicConfig(level=logging.DEBUG,  # Set the logging level
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("app.log"),  # Log to a file
                        logging.StreamHandler()  # Log to console
                    ])

logger = logging.getLogger(__name__)
logger.debug("This is a debug message")


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


# Test function to return the input received
@app.route('/api/echo', methods=['GET'])
def echo():
    input_value = request.args.get('input', default='No input provided')
    logger.info('Received input: %s', input_value)
    return jsonify({'input': input_value})


# Test function to return DB host and DB name
@app.route('/api/dbinfo', methods=['GET'])
def db_info():
    host = os.getenv('DB_HOST', None)
    db_name = os.getenv('DB_NAME', None)
    lang = os.getenv('LANG', None)
    logger.info('DB info - Host: %s, DB Name: %s', host, db_name)
    return jsonify({'host': host, 'db_name': db_name, 'lang (test environ)': lang})


# if __name__ == '__main__':
#     app.run(debug=True)




