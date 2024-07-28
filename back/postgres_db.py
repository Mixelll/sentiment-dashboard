import logging
import psycopg
from psycopg.rows import dict_row
import os
import requests
import boto3
from botocore.exceptions import ClientError


# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# def get_region_from_metadata():
#     try:
#         response = requests.get('http://169.254.169.254/latest/meta-data/placement/region')
#         response.raise_for_status()
#         print(f"Region: {response.text}")
#         return response.text
#     except requests.RequestException as e:
#         print(f"Error fetching region from metadata: {e}")
#         return None
#
# print('REGION', get_region_from_metadata())

def is_running_on_ec2():
    """Check if the code is running on an EC2 instance."""
    try:
        response = requests.get('http://169.254.169.254/latest/meta-data/', timeout=1)
        if response.status_code in [200, 401]:
            return True
        else:
            return False
    except requests.RequestException:
        return False


def fetch_db_credentials():
    """Fetch database credentials from AWS Systems Manager Parameter Store."""
    try:
        ssm_client = boto3.client('ssm', region_name='il-central-1')
        parameters = ssm_client.get_parameters(
            Names=[
                '/hybrid/config/db_host',
                '/hybrid/config/db_port',
                '/hybrid/config/db_user',
                '/hybrid/config/db_password',
                '/hybrid/config/db_name'
            ],
            WithDecryption=True
        )
        return {param['Name'].split('/')[-1]: param['Value'] for param in parameters['Parameters']}
    except ClientError as e:
        logger.error(f"Failed to fetch parameters: {e}")
        return {}


running_on_ec2 = is_running_on_ec2()


if running_on_ec2:
    # Use environment variables for the PostgreSQL credentials
    fetched = fetch_db_credentials()
    conn_info = {
        'host': fetched.get('db_host'),
        'port': fetched.get('db_port', 5432),
        'user': fetched.get('db_user'),
        'password': fetched.get('db_password'),
        # 'dbname': fetched.get('db_name')
    }
else:
    from credentials import postgres_db as postgres_credentials
    conn_info = postgres_credentials.__dict__

logger.info(f"Running on EC2: {running_on_ec2}")
logger.debug(f"Database connection info: {conn_info}")


def fetch_ticker_data(ticker, start_date, end_date, relevance_score=0.):
    """
    Fetches ticker sentiment and relevance score within a specified date range.

    Args:
        ticker (str): The ticker symbol to query.
        start_date (str): The start date of the date range (format YYYY-MM-DD).
        end_date (str): The end date of the date range (format YYYY-MM-DD).
        relevance_score (float): The minimum relevance score to filter by (default = 0.35).

    Returns:
        list: A list of dictionaries containing the fetched data.
    """
    sql_query = f"""
    SELECT 
        sentiment->>'relevance_score' as relevance_score, 
        sentiment->>'ticker_sentiment_score' as sentiment_score, 
        n.time_published, 
        n.source,
        n.authors,
        n.url,
        n.title,
        n.summary,
        n.overall_sentiment_score,
        n.ticker_sentiment as tickers_json,
        n.topics as topics_json
        
    FROM 
        {'public' if running_on_ec2 else 'news_data'}.all_news n,
        json_array_elements(n.ticker_sentiment) as sentiment
    WHERE 
        sentiment->>'ticker' = %s
        AND (sentiment->>'relevance_score')::float > %s
        AND n.time_published > %s
        AND n.time_published < %s
    ORDER BY n.time_published;
    """
    params = (ticker, relevance_score, start_date, end_date)
    # logger.debug(f"Executing query: {sql_query} with params: {params} on DB with host: {os.getenv('DB_HOST', None)}")

    try:
        with psycopg.connect(**conn_info) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql_query, params)
                records = cur.fetchall()

                if records:
                    logger.info(f"Fetched {len(records)} records for ticker {ticker}")
                else:
                    logger.warning(f"No data found for ticker {ticker} with the given parameters.")
                return records

    except psycopg.Error as e:
        logger.error(f"Database error: {e}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
