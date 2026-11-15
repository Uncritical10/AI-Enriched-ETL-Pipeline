import os
import time
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="zomato | Review Intelligence",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- ZOMATO BRAND CSS ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2.5rem;
        max-width: 1200px;
    }

    /* Zomato Hero Banner */
    .zomato-hero {
        background: linear-gradient(135deg, #E23744 0%, #B81D2A 65%, #7A1019 100%);
        padding: 28px 34px;
        border-radius: 18px;
        color: #FFFFFF;
        box-shadow: 0 10px 30px rgba(226, 55, 68, 0.28);
        margin-bottom: 22px;
        border: 1px solid rgba(255, 255, 255, 0.14);
    }
    .zomato-logo {
        font-size: 2.35rem;
        font-weight: 800;
        font-style: italic;
        letter-spacing: -1.5px;
        line-height: 1.1;
        margin: 0;
        color: #FFFFFF;
    }
    .zomato-badge {
        display: inline-block;
        background: rgba(255, 255, 255, 0.18);
        color: #FFFFFF;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        padding: 4px 10px;
        border-radius: 999px;
        margin-left: 10px;
        vertical-align: middle;
        font-style: normal;
    }
    .zomato-subtitle {
        margin: 8px 0 0 0;
        font-size: 0.98rem;
        color: rgba(255, 255, 255, 0.9);
        font-weight: 400;
    }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, #1E1E23 0%, #17171B 100%);
        border: 1px solid rgba(226, 55, 68, 0.25);
        border-top: 3px solid #E23744;
        padding: 16px 20px;
        border-radius: 14px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
    }
    div[data-testid="stMetricLabel"] {
        color: #A0A0AB !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-weight: 800 !important;
        font-size: 1.7rem !important;
    }

    /* Quick Prompt Pill Buttons */
    .stButton > button {
        background-color: #1C1C21;
        color: #F4F4F6;
        border: 1px solid rgba(226, 55, 68, 0.45);
        border-radius: 999px;
        padding: 0.55rem 1rem;
        font-size: 0.84rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #E23744;
        color: #FFFFFF;
        border-color: #E23744;
        transform: translateY(-1px);
        box-shadow: 0 6px 18px rgba(226, 55, 68, 0.35);
    }

    /* Chat Messages */
    div[data-testid="stChatMessage"] {
        background-color: #1A1A1F;
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 14px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }

    /* Chat Input Focus Ring */
    div[data-testid="stChatInput"] textarea:focus {
        border-color: #E23744 !important;
        box-shadow: 0 0 0 1px #E23744 !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #16161A;
        border-right: 1px solid rgba(226, 55, 68, 0.2);
    }
    .sidebar-brand {
        font-size: 1.75rem;
        font-weight: 800;
        font-style: italic;
        color: #E23744;
        letter-spacing: -1px;
        margin-bottom: 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- ENV & CLIENT SETUP ---
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
            SELECT
                r."CAST(r.review_id AS BIGINT)" AS review_id,
                COALESCE(rest.city, 'Unknown') AS city,
                r.rating,
                r.comment
            FROM main_staging.stg_reviews r
            LEFT JOIN main_marts.dim_restaurant rest
                ON r.restaurant_id = rest.restaurant_id
            WHERE r.comment IS NOT NULL
            USING SAMPLE {NEW_REVIEWS} ROWS
        """
        df = conn.execute(query).df()
    finally:
        conn.close()

    df.columns = [col.lower() for col in df.columns]
    return df


def embed_single(text):
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[text],
    )
    return response.data[0].embedding


def embed_with_progress(df):
    all_embeddings = []
    batch_size = 90
    texts = df["comment"].tolist()
    total_batches = (len(texts) + batch_size - 1) // batch_size
    progress = st.progress(0, text="Generating Gemini embeddings...")

    for batch_idx, i in enumerate(range(0, len(texts), batch_size)):
        if i > 0:
            for sec in range(65, 0, -1):
                progress.progress(
                    batch_idx / total_batches,
                    text=f"Rate-limit cooldown: {sec}s remaining (batch {batch_idx + 1}/{total_batches})...",
                )
                time.sleep(1)

        batch = texts[i : i + batch_size]
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
        )
        all_embeddings.extend([item.embedding for item in response.data])

        # Checkpoint to parquet after every batch
        partial_df = df.iloc[: len(all_embeddings)].copy()
        partial_df["embedding"] = all_embeddings
        partial_df.to_parquet(CACHE_FILE)

        progress.progress(
            (batch_idx + 1) / total_batches,
            text=f"Embedded {len(all_embeddings)} / {len(texts)} reviews",
        )

    progress.empty()
    return all_embeddings


def load_reviews():
    if os.path.exists(CACHE_FILE):
        cached_df = pd.read_parquet(CACHE_FILE)
        if len(cached_df) >= NEW_REVIEWS:
            return cached_df

    df = read_reviews_from_duckdb()
    df["embedding"] = embed_with_progress(df)
    df.to_parquet(CACHE_FILE)
    return df


def cosine_similarity(vec_a, vec_b):
    return np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))


def find_similar_reviews(question, df, top_k=TOP_K):
    question_vector = embed_single(question)
    scores = [
        cosine_similarity(question_vector, review_vector)
        for review_vector in df["embedding"]
    ]
    result = df.copy()
    result["similarity"] = np.clip(scores, 0.0, 1.0)
    return result.nlargest(top_k, "similarity")


def ask_llm(question, top_reviews):
    context = ""
    for _, row in top_reviews.iterrows():
        context += f"({row['city']}, {row['rating']}★) {row['comment']}\n"

    system_prompt = (
        "You are a Zomato customer experience analyst. Answer ONLY using the "
        "customer reviews provided. Use concise bullet points for key findings, "
        "and explicitly state if the reviews don't cover the question."
    )
    user_prompt = f"Question: {question}\n\nReviews:\n{context}"

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content



review_df = load_reviews()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<p class="sidebar-brand">zomato</p>', unsafe_allow_html=True)
    st.caption(f"AI Review Copilot • `{CHAT_MODEL}`")
    st.divider()

    cities = ["All Cities"] + sorted(review_df["city"].dropna().unique().tolist())
    selected_city = st.selectbox("📍 City", cities)

    rating_range = st.slider(
        "⭐ Star Rating Range",
        min_value=1.0,
        max_value=5.0,
        value=(1.0, 5.0),
        step=0.5,
    )

    top_k = st.slider("🔎 Top Matching Reviews", min_value=3, max_value=10, value=5)

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    with col_b:
        if st.button("🔄 Resample", use_container_width=True):
            if os.path.exists(CACHE_FILE):
                os.remove(CACHE_FILE)
            st.rerun()

# Apply filters
filtered_df = review_df[
    (review_df["rating"] >= rating_range[0]) & (review_df["rating"] <= rating_range[1])
]
if selected_city != "All Cities":
    filtered_df = filtered_df[filtered_df["city"] == selected_city]

# --- ZOMATO HERO BANNER ---
st.markdown(
    """
    <div class="zomato-hero">
        <div class="zomato-logo">
            zomato <span class="zomato-badge">AI Review Intelligence</span>
        </div>
        <p class="zomato-subtitle">
            Discover customer sentiment, delivery bottlenecks, and dish feedback across your DuckDB data warehouse.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


m1, m2, m3, m4 = st.columns(4)
m1.metric("Indexed Reviews", len(filtered_df), f"of {len(review_df)} loaded")
avg_rating = filtered_df["rating"].mean() if not filtered_df.empty else 0.0
m2.metric("Average Rating", f"{avg_rating:.2f} ★")
low_ratings = int((filtered_df["rating"] <= 2.0).sum()) if not filtered_df.empty else 0
m3.metric("Low Ratings (≤2★)", low_ratings)
m4.metric("Cities Active", filtered_df["city"].nunique())

st.markdown("#### 🔥 Popular Questions")
sample_questions = [
    "What are the most common complaints about delivery?",
    "What do customers love most about the food?",
    "Are there issues with packaging or cold food?",
    "Summarize the main pain points in 1–2 star reviews.",
]

cols = st.columns(len(sample_questions))
triggered_prompt = None
for idx, prompt_text in enumerate(sample_questions):
    if cols[idx].button(prompt_text, key=f"pill_{idx}", use_container_width=True):
        triggered_prompt = prompt_text

st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    avatar = "🧑" if msg["role"] == "user" else "🍽️"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        if "sources" in msg and not msg["sources"].empty:
            with st.expander("📋 View matching customer reviews"):
                st.dataframe(
                    msg["sources"][["city", "rating", "similarity", "comment"]],
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "city": st.column_config.TextColumn("City", width="small"),
                        "rating": st.column_config.NumberColumn("Rating", format="%.1f ★", width="small"),
                        "similarity": st.column_config.ProgressColumn(
                            "Relevance", min_value=0.0, max_value=1.0, format="%.2f"
                        ),
                        "comment": st.column_config.TextColumn("Review Comment", width="large"),
                    },
                )

user_input = st.chat_input("Ask Zomato AI about delivery times, food quality, packaging...")
active_question = triggered_prompt or user_input

if active_question:
    if filtered_df.empty:
        st.warning("No reviews match your current filters. Adjust the City or Star Rating slider in the sidebar.")
    else:
        st.session_state.messages.append({"role": "user", "content": active_question})
        with st.chat_message("user", avatar="🧑"):
            st.markdown(active_question)

        with st.chat_message("assistant", avatar="🍽️"):
            try:
                with st.spinner("Scanning customer reviews..."):
                    top_reviews = find_similar_reviews(active_question, filtered_df, top_k=top_k)
                    answer = ask_llm(active_question, top_reviews)

                st.markdown(answer)
                with st.expander("📋 View matching customer reviews"):
                    st.dataframe(
                        top_reviews[["city", "rating", "similarity", "comment"]],
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "city": st.column_config.TextColumn("City", width="small"),
                            "rating": st.column_config.NumberColumn("Rating", format="%.1f ★", width="small"),
                            "similarity": st.column_config.ProgressColumn(
                                "Relevance", min_value=0.0, max_value=1.0, format="%.2f"
                            ),
                            "comment": st.column_config.TextColumn("Review Comment", width="large"),
                        },
                    )

                st.session_state.messages.append(
                    {"role": "assistant", "content": answer, "sources": top_reviews}
                )
            except Exception as e:
                st.exception(e)
