import psycopg
from psycopg.rows import dict_row
from credentials import postgres_db as postgres_credentials

conn_info = postgres_credentials.__dict__


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

    # SQL query using parameterized inputs
    sql_query = """
    SELECT 
        sentiment->>'relevance_score' as relevance_score, 
        sentiment->>'ticker_sentiment_score' as sentiment_score, 
        n.time_published, 
        n.source_domain,
        n.url,
        n.title,
        n.summary,
        n.ticker_sentiment as json_data
    FROM 
        news_data.all_news n,
        json_array_elements(n.ticker_sentiment) as sentiment
    WHERE 
        sentiment->>'ticker' = %s
        AND (sentiment->>'relevance_score')::float > %s
        AND n.time_published > %s
        AND n.time_published < %s
    ORDER BY n.time_published;
    """

    try:
        # Connect to the database using a with statement, which automatically handles closing
        with psycopg.connect(**conn_info) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Execute the query with parameters
                cur.execute(sql_query, (ticker, relevance_score, start_date, end_date))

                # Fetch all rows from the last executed query
                records = cur.fetchall()

                # Check if any records were found
                if records:
                    pass
                    # print(f"Data for ticker {ticker}:")
                    # print(records[-1])
                    # for row in records:
                    #     print(f"Relevance Score: {row['relevance_score']}, Sentiment Score: {row['sentiment_score']}, Time Published: {row['time_published']}")
                    # for row in records:
                    #     print(row)
                else:
                    print("No data found for the given parameters.")
                return records

    except psycopg.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

