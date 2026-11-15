import os
import re
import json
from pathlib import Path
import duckdb
import pandas as pd
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="zomato | Food & Order Data Explorer",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- ZOMATO RED & WHITE FOOD-DISCOVERY CSS ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #1C1C1C;
    }

    /* Main App Canvas */
    .stApp {
        background-color: #F8F8FA;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    /* Zomato Hero Banner */
    .zomato-hero {
        background: linear-gradient(125deg, #E23744 0%, #CB202D 60%, #9E1420 100%);
        padding: 32px 36px;
        border-radius: 20px;
        color: #FFFFFF;
        box-shadow: 0 12px 28px rgba(226, 55, 68, 0.22);
        margin-bottom: 24px;
        position: relative;
        overflow: hidden;
    }
    .zomato-brand-row {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
    }
    .zomato-wordmark {
        font-size: 2.5rem;
        font-weight: 800;
        font-style: italic;
        letter-spacing: -1.5px;
        line-height: 1;
        color: #FFFFFF;
        margin: 0;
    }
    .zomato-pill {
        background: rgba(255, 255, 255, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.35);
        color: #FFFFFF;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        padding: 5px 12px;
        border-radius: 999px;
    }
    .zomato-hero-desc {
        margin: 10px 0 0 0;
        font-size: 1rem;
        color: rgba(255, 255, 255, 0.94);
        font-weight: 400;
        max-width: 720px;
    }

    /* Section Headings */
    .section-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #1C1C1C;
        margin: 0.5rem 0 0.75rem 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Restaurant / Discovery Cards */
    .discovery-card {
        background: #FFFFFF;
        border: 1px solid #EBEBEF;
        border-radius: 16px;
        padding: 18px 20px;
        box-shadow: 0 4px 14px rgba(28, 28, 28, 0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        height: 100%;
        margin-bottom: 14px;
    }
    .discovery-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 24px rgba(226, 55, 68, 0.12);
        border-color: rgba(226, 55, 68, 0.35);
    }
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 10px;
        margin-bottom: 8px;
    }
    .card-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1C1C1C;
        margin: 0;
        line-height: 1.3;
    }
    .rating-badge {
        background-color: #24963F;
        color: #FFFFFF;
        font-size: 0.78rem;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        white-space: nowrap;
    }
    .card-meta {
        font-size: 0.84rem;
        color: #696969;
        margin-bottom: 12px;
    }
    .card-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-top: 1px dashed #ECECEF;
        padding-top: 10px;
        font-size: 0.82rem;
        color: #4F4F4F;
        font-weight: 600;
    }
    .card-highlight {
        color: #E23744;
        font-weight: 700;
    }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #EBEBEF;
        border-left: 4px solid #E23744;
        padding: 16px 20px;
        border-radius: 14px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }
    div[data-testid="stMetricLabel"] {
        color: #696969 !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetricValue"] {
        color: #1C1C1C !important;
        font-weight: 800 !important;
        font-size: 1.6rem !important;
    }

    /* Primary & Quick-Prompt Buttons */
    .stButton > button {
        background-color: #FFFFFF;
        color: #1C1C1C;
        border: 1px solid #E0E0E5;
        border-radius: 12px;
        padding: 0.55rem 1rem;
        font-size: 0.85rem;
        font-weight: 600;
        transition: all 0.18s ease;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
    }
    .stButton > button:hover {
        background-color: #FFF5F6;
        color: #E23744;
        border-color: #E23744;
        transform: translateY(-1px);
    }

    /* Form Submit Button (Zomato Crimson CTA) */
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #E23744 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        padding: 0.6rem 1.4rem !important;
        box-shadow: 0 4px 14px rgba(226, 55, 68, 0.3) !important;
    }
    div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #CB202D !important;
        color: #FFFFFF !important;
    }

    /* Search Input Styling */
    div[data-testid="stTextInput"] input {
        background-color: #FFFFFF !important;
        border: 1.5px solid #E2E2E8 !important;
        border-radius: 12px !important;
        padding: 0.65rem 1rem !important;
        font-size: 0.95rem !important;
        color: #1C1C1C !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #E23744 !important;
        box-shadow: 0 0 0 3px rgba(226, 55, 68, 0.14) !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #ECECEF;
    }
    .sidebar-logo {
        font-size: 1.9rem;
        font-weight: 800;
        font-style: italic;
        color: #E23744;
        letter-spacing: -1px;
        margin-bottom: 2px;
    }
    .schema-chip {
        display: inline-block;
        background: #FFF2F3;
        color: #CB202D;
        border: 1px solid #FFD6DA;
        font-size: 0.76rem;
        font-weight: 600;
        padding: 4px 9px;
        border-radius: 8px;
        margin: 3px 3px 3px 0;
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

MODEL = "gemini-3.5-flash"
DUCKDB_PATH = os.getenv("DUCKDB_PATH", "C:/duck/zomato.duckdb")

FORBIDDEN_WORDS = [
    "drop", "delete", "truncate", "alter", "update",
    "insert", "create", "replace", "grant", "revoke",
    "attach", "detach", "copy", "export", "import"
]

EXAMPLE_QUESTIONS = [
    "Top 10 cities by GMV",
    "Which cuisine has the most orders?",
    "Average delivery time by city, worst first",
    "Cancel rate by payment method",
]

client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

SCHEMA = """
Tables available in DuckDB (schema: main_marts). Always prefix tables with main_marts.<table_name>:

main_marts.fct_orders(order_id, order_date, customer_id, restaurant_id, city, cuisine,
                      payment_method, order_status, is_delivered, sales_amount, discount,
                      delivery_fee, gst, customer_rating, delivery_time_min)
main_marts.dim_restaurant(restaurant_id, restaurant_name, city, cuisine, rating, cost_for_two)
main_marts.dim_customer(customer_id, customer_name, age, age_segment, gender, city)
main_marts.mart_daily_city_revenue(order_date, city, orders, cancel_rate, gmv, aov)
main_marts.mart_restaurant_performance(restaurant_id, restaurant_name, city, cuisine,
                                       orders, revenue, avg_customer_rating, cancel_rate)
main_marts.mart_delivery_sla(city, order_hour, delivered_orders, p50_delivery_min, late_rate)

Note: gmv means delivered revenue. Prefer the mart_* tables when they fit the question.
"""

SYSTEM_PROMPT = f"""
You are a DuckDB SQL expert. Write ONE DuckDB-compatible SELECT query that answers the question.

Rules:
- SELECT or WITH (CTE) queries only, never modify data.
- Always qualify table names with main_marts (e.g., main_marts.fct_orders).
- Use DuckDB SQL syntax (e.g., DATE_TRUNC('month', order_date), ILIKE, NULLIF).
- Add a LIMIT of 100 or less, unless the question asks for a single aggregated total.
- Reply as JSON in this exact format: {{"sql": "your query here"}}

{SCHEMA}
"""


def generate_sql(question: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
    )
    answer = response.choices[0].message.content
    sql = json.loads(answer)["sql"]
    return sql.strip().rstrip(";")


def is_safe(sql: str) -> bool:
    lowered = sql.lower().strip()
    if not lowered.startswith("select") and not lowered.startswith("with"):
        return False
    for word in FORBIDDEN_WORDS:
        if re.search(rf"\b{word}\b", lowered):
            return False
    return True


def run_query(sql: str) -> pd.DataFrame:
    conn = duckdb.connect(DUCKDB_PATH, read_only=True)
    try:
        return conn.execute(sql).df()
    finally:
        conn.close()


@st.cache_data(ttl=300)
def get_featured_restaurants() -> pd.DataFrame:
    """Fetch top-rated restaurants for the food-discovery showcase cards."""
    try:
        conn = duckdb.connect(DUCKDB_PATH, read_only=True)
        try:
            query = """
                SELECT
                    restaurant_name,
                    city,
                    cuisine,
                    rating,
                    cost_for_two
                FROM main_marts.dim_restaurant
                WHERE restaurant_name IS NOT NULL
                ORDER BY rating DESC NULLS LAST
                LIMIT 3
            """
            return conn.execute(query).df()
        finally:
            conn.close()
    except Exception:
        return pd.DataFrame()


def render_result_cards(df: pd.DataFrame):
    """Render top query rows as clean Zomato-style discovery cards."""
    preview_df = df.head(6)
    cols = st.columns(3)
    for idx, (_, row) in enumerate(preview_df.iterrows()):
        col = cols[idx % 3]
        primary_title = str(row.iloc[0])
        rating_val = None
        for r_col in ["rating", "avg_customer_rating", "customer_rating"]:
            if r_col in df.columns and pd.notnull(row[r_col]):
                rating_val = f"{float(row[r_col]):.1f} ★"
                break

        details = []
        for c in df.columns[1:]:
            if c in ["rating", "avg_customer_rating", "customer_rating"]:
                continue
            val = row[c]
            if isinstance(val, float):
                val_str = f"{val:,.2f}"
            elif isinstance(val, int):
                val_str = f"{val:,}"
            else:
                val_str = str(val)
            details.append(f"<span><b>{c.replace('_', ' ').title()}:</b> {val_str}</span>")

        meta_html = " &bull; ".join(details[:2]) if details else "DuckDB Mart Record"
        footer_html = details[2] if len(details) > 2 else f"<span class='card-highlight'>Rank #{idx + 1}</span>"
        badge_html = f"<span class='rating-badge'>{rating_val}</span>" if rating_val else ""

        with col:
            st.markdown(
                f"""
                <div class="discovery-card">
                    <div class="card-header">
                        <p class="card-title">{primary_title}</p>
                        {badge_html}
                    </div>
                    <div class="card-meta">{meta_html}</div>
                    <div class="card-footer">{footer_html}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# --- SESSION STATE ---
if "active_question" not in st.session_state:
    st.session_state.active_question = ""

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<p class="sidebar-logo">zomato</p>', unsafe_allow_html=True)
    st.caption(f"AI Data Explorer • `{MODEL}`")
    st.divider()

    st.markdown("**🔥 Popular Searches**")
    for idx, q in enumerate(EXAMPLE_QUESTIONS):
        if st.button(q, key=f"sidebar_q_{idx}", use_container_width=True):
            st.session_state.active_question = q

    st.divider()
    st.markdown("**🗄️ Connected Data Marts**")
    mart_names = [
        "fct_orders",
        "dim_restaurant",
        "dim_customer",
        "mart_daily_city_revenue",
        "mart_restaurant_performance",
        "mart_delivery_sla",
    ]
    chips_html = "".join([f'<span class="schema-chip">{m}</span>' for m in mart_names])
    st.markdown(chips_html, unsafe_allow_html=True)

    st.divider()
    if st.session_state.active_question:
        if st.button("🧹 Clear Search", use_container_width=True):
            st.session_state.active_question = ""
            st.rerun()

# --- HERO BANNER ---
st.markdown(
    """
    <div class="zomato-hero">
        <div class="zomato-brand-row">
            <h1 class="zomato-wordmark">zomato</h1>
            <span class="zomato-pill">Food & Order Intelligence</span>
        </div>
        <p class="zomato-hero-desc">
            Discover top cuisines, city-wise GMV, restaurant ratings, and delivery SLAs by asking questions in plain English.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- FEATURED RESTAURANTS SHOWCASE (WHEN IDLE) ---
featured_df = get_featured_restaurants()
if not st.session_state.active_question and not featured_df.empty:
    st.markdown('<div class="section-title">🍴 Featured Top-Rated Spots</div>', unsafe_allow_html=True)
    f_cols = st.columns(len(featured_df))
    for idx, (_, rest) in enumerate(featured_df.iterrows()):
        with f_cols[idx]:
            rating_str = f"{float(rest['rating']):.1f} ★" if pd.notnull(rest["rating"]) else "New"
            cost_str = f"₹{int(rest['cost_for_two']):,} for two" if pd.notnull(rest["cost_for_two"]) else "Casual Dining"
            st.markdown(
                f"""
                <div class="discovery-card">
                    <div class="card-header">
                        <p class="card-title">{rest['restaurant_name']}</p>
                        <span class="rating-badge">{rating_str}</span>
                    </div>
                    <div class="card-meta">{rest['cuisine']} &bull; {rest['city']}</div>
                    <div class="card-footer">
                        <span>{cost_str}</span>
                        <span class="card-highlight">Top Pick</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# --- SEARCH BAR FORM ---
st.markdown('<div class="section-title">🔍 Ask Anything About Your Orders & Restaurants</div>', unsafe_allow_html=True)
with st.form("zomato_sql_form", clear_on_submit=False):
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        typed_question = st.text_input(
            "Ask a question",
            value=st.session_state.active_question,
            placeholder="e.g. Top 10 restaurants by revenue in Bangalore...",
            label_visibility="collapsed",
        )
    with col_btn:
        submitted = st.form_submit_button("Explore", use_container_width=True)

if submitted and typed_question.strip():
    st.session_state.active_question = typed_question.strip()

# --- QUICK PROMPT PILLS ---
pill_cols = st.columns(len(EXAMPLE_QUESTIONS))
for idx, q in enumerate(EXAMPLE_QUESTIONS):
    if pill_cols[idx].button(q, key=f"pill_{idx}", use_container_width=True):
        st.session_state.active_question = q
        st.rerun()

# --- QUERY EXECUTION & RESULTS ---
current_query = st.session_state.active_question

if current_query:
    st.divider()
    with st.spinner("Translating question into DuckDB SQL & fetching insights..."):
        sql = generate_sql(current_query)

    if not is_safe(sql):
        st.error("The generated SQL query was blocked by safety rules. Please rephrase your question.")
        with st.expander("View blocked SQL"):
            st.code(sql, language="sql")
    else:
        try:
            df = run_query(sql)

            # Summary KPI Strip
            k1, k2, k3 = st.columns(3)
            k1.metric("Results Returned", f"{len(df):,} rows")
            k2.metric("Columns Analyzed", f"{len(df.columns)}")
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            if numeric_cols:
                top_metric_col = numeric_cols[-1]
                k3.metric(
                    f"Top {top_metric_col.replace('_', ' ').title()}",
                    f"{df[top_metric_col].max():,.2f}",
                )
            else:
                k3.metric("Data Source", "DuckDB Marts")

            # Clean Tabbed Views: Cards + Table, Chart, and SQL
            tab_cards, tab_table, tab_sql = st.tabs(
                ["🍽️ Discovery Cards & Chart", "📋 Full Data Table", "🧾 Generated SQL"]
            )

            with tab_cards:
                if df.empty:
                    st.info("No matching records found in DuckDB for this question.")
                else:
                    render_result_cards(df)
                    if len(df.columns) == 2 and pd.api.types.is_numeric_dtype(df.iloc[:, 1]):
                        st.markdown('<div class="section-title">📊 Visual Breakdown</div>', unsafe_allow_html=True)
                        st.bar_chart(df, x=df.columns[0], y=df.columns[1], color="#E23744")

            with tab_table:
                st.dataframe(df, hide_index=True, use_container_width=True)

            with tab_sql:
                st.code(sql, language="sql")

        except Exception as e:
            st.error(f"Error running DuckDB query: {e}")
            with st.expander("Inspect generated SQL"):
                st.code(sql, language="sql")
