import os
import json
from pathlib import Path
import duckdb
from openai import OpenAI
from dotenv import load_dotenv

# 1. Load environment variables (.env in mounted dbt_project root or local cwd)
env_path = Path("/opt/airflow/dbt_project/.env")
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# 2. Configuration
MODEL = "gemini-3.5-flash"
DEFAULT_DB = "C:/duck/zomato.duckdb" if os.name == "nt" else "/opt/airflow/duck/zomato.duckdb"
DUCKDB_PATH = os.getenv("DUCKDB_PATH", DEFAULT_DB)
SAMPLE_N = int(os.getenv("ENRICH_SAMPLE_N", "50"))

TOPICS = ["food quality", "delivery", "pricing", "service", "packaging", "other"]

client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

SYSTEM_PROMPT = f"""
You classify customer reviews for a food delivery app.

For the review you are given, return:
- sentiment_label: positive, negative, or neutral
- sentiment_score: a number between -1.0 and 1.0
- topic: one of {TOPICS}
- key_issue: a short phrase of 6 words or less that describes the main issue in the review, if any. If there is no issue, return null

Reply as JSON in this exact format:
{{
    "sentiment_label": "<sentiment_label>",
    "sentiment_score": <sentiment_score>,
    "topic": "<topic>",
    "key_issue": "<key_issue>"
}}
"""


def get_connection():
    return duckdb.connect(DUCKDB_PATH)


def create_output_table(conn):
    conn.execute("CREATE SCHEMA IF NOT EXISTS ai;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai.review_enriched (
            review_id BIGINT,
            sentiment_label VARCHAR,
            sentiment_score DOUBLE,
            topic VARCHAR,
            key_issue VARCHAR,
            model VARCHAR,
            enriched_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
    """)


def get_reviews_to_enrich(conn):
    query = f"""
        SELECT r.review_id, r.comment
        FROM raw.reviews r
        WHERE r.comment IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM ai.review_enriched e
              WHERE CAST(e.review_id AS BIGINT) = r.review_id
          )
        LIMIT {SAMPLE_N};
    """
    return conn.execute(query).fetchall()


def classify_review(comment):
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": comment},
        ],
    )
    answer = response.choices[0].message.content
    return json.loads(answer)


def save_results(conn, results):
    """Insert all enriched rows into DuckDB in one batch."""
    if not results:
        return
    print(f"Saving {len(results)} enriched reviews to DuckDB...")
    conn.executemany(
        """
        INSERT INTO ai.review_enriched
            (review_id, sentiment_label, sentiment_score, topic, key_issue, model)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        results,
    )


def main():
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("Missing GEMINI_API_KEY. Set it in /opt/airflow/dbt_project/.env or environment variables.")

    conn = get_connection()
    try:
        create_output_table(conn)
        reviews = get_reviews_to_enrich(conn)

        if len(reviews) == 0:
            print("No new reviews to enrich.")
            return

        print(f"Enriching {len(reviews)} reviews using {MODEL}...")

        results = []
        for review_id, comment in reviews:
            print(f"Classifying review {review_id}: {comment}")
            try:
                labels = classify_review(comment)
                print(f"Labels for review {review_id}: {labels}")
                results.append((
                    review_id,
                    labels["sentiment_label"],
                    labels["sentiment_score"],
                    labels["topic"],
                    labels.get("key_issue"),
                    MODEL,
                ))
            except Exception as e:
                print(f"Error occurred while classifying review {review_id}: {e}")

        save_results(conn, results)
        print(f"Saved {len(results)} enriched reviews to DuckDB.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
