import os
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import time  # add this at the top with your other imports

# Load .env from your project folder (or current directory)
env_path = Path("C:/ETL-Zomato/zomato/.env")
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

EMBEDDING_MODEL = "gemini-embedding-001"
CHAT_MODEL = "gemini-3.5-flash"
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "C:/duck/zomato.duckdb")

NEW_REVIEWS = 500
TOP_K = 5
CACHE_FILE = "review_embeddings.parquet"

client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)


def read_reviews_from_duckdb():
    conn = duckdb.connect(DUCKDB_PATH, read_only=True)
    try:
        query = f"""
            SELECT review_id, city, rating, comment
            FROM main_staging.stg_reviews
            WHERE comment IS NOT NULL
            USING SAMPLE {NEW_REVIEWS} ROWS
        """
        df = conn.execute(query).df()
    finally:
        conn.close()

    df.columns = [col.lower() for col in df.columns]
    return df


def embed(texts):
    # Batch in chunks of 100 to stay within Gemini embedding batch limits
    embeddings = []
    for i in range(0, len(texts), 100):
        batch = texts[i : i + 100]
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
        )
        embeddings.extend([item.embedding for item in response.data])
    return embeddings


@st.cache_data
def load_reviews():
    if os.path.exists(CACHE_FILE):
        return pd.read_parquet(CACHE_FILE)

    df = read_reviews_from_duckdb()
    df["embedding"] = embed(df["comment"].tolist())
    df.to_parquet(CACHE_FILE)
    return df


st.title("Chat with your Zomato Reviews")
st.caption(f"Searching {NEW_REVIEWS} reviews, answering with {CHAT_MODEL}")


def cosine_similarity(vec_a, vec_b):
    return np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))


def find_similar_reviews(question, df):
    question_vector = embed([question])[0]

    scores = [
        cosine_similarity(question_vector, review_vector)
        for review_vector in df["embedding"]
    ]

    df = df.copy()
    df["score"] = scores
    return df.nlargest(TOP_K, "score")


def ask_llm(question, top_reviews):
    context = ""
    for _, row in top_reviews.iterrows():
        context += f"({row['city']}, {row['rating']} stars) {row['comment']}\n"

    system_prompt = (
        "Answer ONLY using the customer reviews provided. "
        "Be concise. If the reviews don't cover it, say so."
    )

    user_prompt = f"Question: {question}\n\nCustomer Reviews:\n{context}"
