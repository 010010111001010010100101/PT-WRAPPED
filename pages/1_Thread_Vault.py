"""PT Thread Vault — searchable archive of every substantial PT thread,
with a permanent link so it survives PT's 3-month lock. Reads archive.db
(built by pt_webapp/build_archive.py). No raw post data.
"""
import streamlit as st
import html, os, sqlite3

DB = os.path.join(os.path.dirname(__file__), "..", "data", "archive.db")
PT = "https://www.phantasytour.com/bands/1/threads"

st.set_page_config(page_title="PT Thread Vault", page_icon="🧵", layout="centered")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&display=swap');
h1 {
    font-family: 'Space Grotesk', 'Segoe UI', sans-serif !important;
    background: linear-gradient(90deg, #ffd166, #ff8a3d, #ff5c8a, #9b8cff, #5ce0c0);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: -0.5px;
}
.block-container { padding-top: 2.2rem; max-width: 820px; }
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(620px at 12% 8%,  rgba(255,138,61,0.14), transparent 65%),
        radial-gradient(540px at 88% 14%, rgba(124,92,255,0.18), transparent 65%),
        radial-gradient(700px at 75% 75%, rgba(217,43,75,0.12), transparent 65%),
        #0f0f14;
    background-attachment: fixed;
}
.trow {
    display:flex; align-items:center; gap:14px; background:#14141c;
    border:1px solid #26262f; border-radius:12px; padding:12px 18px; margin:6px 0;
}
.trow a { color:#e8e6e3; text-decoration:none; font-size:16px; flex:1; }
.trow a:hover { color:#9b8cff; }
.trow .meta { color:#8a8a96; font-size:13px; white-space:nowrap; }
.trow .cnt { color:#ff8a3d; font-weight:700; white-space:nowrap; }
</style>""", unsafe_allow_html=True)


@st.cache_resource
def _db():
    return sqlite3.connect(DB, check_same_thread=False)


@st.cache_data
def _meta():
    try:
        return dict(_db().execute("SELECT key, value FROM meta"))
    except sqlite3.OperationalError:
        return {}


@st.cache_data(show_spinner=False)
def _search(term, setlists, sort, limit=150):
    order = {"Most posts": "posts DESC",
             "Newest": "first_date DESC",
             "Oldest": "first_date ASC"}[sort]
    where = ["1=1"]
    params = []
    if term:
        where.append("subject LIKE ?")
        params.append(f"%{term}%")
    if not setlists:
        where.append("is_setlist = 0")
    params.append(limit)
    return _db().execute(
        f"SELECT subject, slug, topic_id, posts, first_date, last_date FROM threads "
        f"WHERE {' AND '.join(where)} ORDER BY {order} LIMIT ?", params).fetchall()


if not os.path.exists(DB):
    st.error("Thread archive missing — run build_archive.py first.")
    st.stop()

meta = _meta()
st.title("PT Thread Vault")
st.caption(f"Every PT thread with 100+ posts — {int(meta.get('thread_count', 0)):,} of them, "
           f"{meta.get('span_lo','')[:4]}–{meta.get('span_hi','')[:4]}. "
           "Threads lock after 3 months, but the link lives here forever. Search and dig in.")

c1, c2 = st.columns([3, 2])
term = c1.text_input("Search thread titles", placeholder="e.g. coventry, sphere, treason").strip()
sort = c2.selectbox("Sort", ["Most posts", "Newest", "Oldest"])
setlists = st.checkbox("Include setlist threads", value=False)

rows = _search(term, setlists, sort)
if not rows:
    st.info("No threads match. Try a shorter or different term.")
else:
    st.caption(f"Showing {len(rows)} thread{'s' if len(rows) != 1 else ''}"
               + (" (capped at 150 — narrow your search for more)" if len(rows) == 150 else ""))
    for subject, slug, tid, posts, first, last in rows:
        url = f"{PT}/{tid}/{slug}" if tid else "#"
        span = first[:7] if first[:7] == (last or "")[:7] else f"{first[:7]} → {last[:7]}"
        st.markdown(
            f"""<div class="trow">
              <a href="{url}" target="_blank">{html.escape(subject or '(untitled)')}</a>
              <span class="meta">{span}</span>
              <span class="cnt">{posts:,}</span>
            </div>""",
            unsafe_allow_html=True,
        )
