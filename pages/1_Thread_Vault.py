"""PT Thread Vault — searchable archive of every substantial PT thread,
with a permanent link so it survives PT's 3-month lock. Reads archive.db
(built by pt_webapp/build_archive.py). No raw post data.
"""
import streamlit as st
import datetime, gzip, html, os, re, shutil, sqlite3
from collections import Counter, defaultdict

DB = os.path.join(os.path.dirname(__file__), "..", "data", "archive.db")
GZ = DB + ".gz"
PT = "https://www.phantasytour.com/bands/1/threads"


def _ensure_db():
    """The repo ships archive.db.gz (the raw .db is over GitHub's 100 MB limit).
    Decompress it on first boot, and refresh if a newer .gz was pulled. Write to
    a temp file + atomic rename so a concurrent boot request never opens a
    half-written DB."""
    if not os.path.exists(GZ):
        return  # local dev: a raw .db may already be present with no .gz
    if os.path.exists(DB) and os.path.getmtime(DB) >= os.path.getmtime(GZ):
        return
    tmp = f"{DB}.tmp.{os.getpid()}"
    with gzip.open(GZ, "rb") as fin, open(tmp, "wb") as fout:
        shutil.copyfileobj(fin, fout, length=1 << 20)
    os.replace(tmp, DB)

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
def _adb():
    return sqlite3.connect(DB, check_same_thread=False)


@st.cache_data
def _ameta():
    try:
        return dict(_adb().execute("SELECT key, value FROM meta"))
    except sqlite3.OperationalError:
        return {}


@st.cache_data
def _has_starter():
    """Older archives (built before the starter column existed) lack it — detect so
    the username search degrades cleanly instead of throwing 'no such column'."""
    return any(r[1] == "starter"
               for r in _adb().execute("PRAGMA table_info(threads)").fetchall())


@st.cache_data(show_spinner=False)
def _search(term, user, setlists, big, min50, sort, yr_lo, yr_hi, limit=150):
    # Span/intensity use julianday on the YYYY-MM-DD date strings; +1 day avoids
    # divide-by-zero on same-day threads. ORDER strings are fixed (not user input).
    order = {
        "Most posts": "posts DESC",
        "Least posts": "posts ASC",
        "Newest": "first_date DESC",
        "Oldest": "first_date ASC",
        "Recently active": "last_date DESC, posts DESC",
        "Longest-running": "(julianday(last_date) - julianday(first_date)) DESC, posts DESC",
        "Fastest growing": "(posts * 1.0 / (julianday(last_date) - julianday(first_date) + 1)) DESC",
        "Title A–Z": "subject COLLATE NOCASE ASC",
    }[sort]
    where = ["1=1"]
    params = []
    if term:
        where.append("subject LIKE ?")
        params.append(f"%{term}%")
    if user and _has_starter():
        where.append("starter LIKE ?")
        params.append(f"%{user}%")
    if not setlists:
        where.append("is_setlist = 0")
    if not big:
        where.append("posts <= 499")
    if min50:
        where.append("posts >= 50")
    where.append("first_date >= ? AND first_date <= ?")
    params.extend([f"{yr_lo}-01-01", f"{yr_hi}-12-31"])
    params.append(limit)
    starter_col = "starter" if _has_starter() else "'' AS starter"
    return _adb().execute(
        f"SELECT subject, slug, topic_id, posts, first_date, last_date, {starter_col} "
        f"FROM threads WHERE {' AND '.join(where)} ORDER BY {order} LIMIT ?", params).fetchall()


# Words too common or structural to be interesting as thread-title keywords.
STOP_WORDS = {
    'a','about','above','after','ah','all','also','amp','an','and','any','are','as','at',
    'back','be','been','before','being','below','bold','both','br','but','by','can','cant',
    'code','color','com','come','could','did','didnt','do','does','doesnt','dont','down',
    'during','each','either','else','even','every','for','from','get','good','got','gt','had',
    'has','have','he','her','here','hes','hey','his','how','http','https','i','id','if','ill',
    'im','img','in','into','is','it','its','ive','just','know','like','ll','lol','look','lt',
    'make','may','me','might','more','my','nah','nbsp','need','neither','new','no','nope','nor',
    'not','now','nt','of','off','oh','ok','okay','on','one','only','or','our','out','over',
    'post','posts','pt','quote','re','right','s','said','same','say','see','shall','she','shes',
    'should','size','so','some','spoiler','still','t','take','than','that','thats','the','their',
    'them','then','there','these','they','theyre','think','this','those','thread','through',
    'time','to','too','two','uh','um','under','up','url','used','user','ve','very','want','was',
    'way','we','well','were','what','when','where','which','who','whom','why','will','with',
    'wont','would','wow','www','yeah','yep','yes','yet','you','your','youre',
}


@st.cache_data(show_spinner=False)
def _keywords_by_year():
    """{year -> Counter(word)} from thread titles, setlist threads excluded."""
    by_year = defaultdict(Counter)
    for subj, yr in _adb().execute(
            "SELECT subject, substr(first_date, 1, 4) FROM threads WHERE is_setlist = 0"):
        if not yr:
            continue
        toks = [w for w in re.findall(r"[a-z]{3,}", (subj or "").lower())
                if w not in STOP_WORDS]
        by_year[yr].update(toks)
    return dict(by_year)


_ensure_db()

if not os.path.exists(DB):
    st.error("Thread archive missing — run build_archive.py first.")
    st.stop()

# Guard against a stale/empty archive.db on the host (Streamlit Cloud can keep
# an old copy if the file's git blob hasn't changed) — fail with a clear note
# instead of a raw "no such table" traceback.
if not _adb().execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='threads'").fetchone():
    # Drop caches so a transient empty read (boot race / mid-sync) self-heals on the
    # next refresh instead of being frozen in cache.
    _ameta.clear()
    _adb.clear()
    st.error("Thread archive is present but empty on this host — the deployed copy "
             "is stale. Reboot the app, or just refresh in a few seconds.")
    st.stop()

meta = _ameta()
try:
    st.page_link("app.py", label="← Back to PT Wrapped")
except Exception:
    st.markdown("[← Back to PT Wrapped](/)")
st.title("PT Thread Vault")
st.caption(f"A growing archive of every PT thread — "
           f"{int(meta.get('thread_count', 0)):,} so far. Recent years (≈2017–{meta.get('span_hi','')[:4]}) "
           "are complete; older years are still backfilling. "
           "Threads lock after 3 months, but the link lives here forever. Search and dig in.")

with st.expander("🔤 Top keywords in thread titles", expanded=False):
    kw = _keywords_by_year()
    years_avail = sorted((y for y in kw if y.isdigit()), reverse=True)
    k1, k2 = st.columns([2, 3])
    sel_yr = k1.selectbox("Year", ["All-time"] + years_avail, key="kw_year")
    top_n = k2.slider("How many", 10, 40, 20, key="kw_n")
    if sel_yr == "All-time":
        counts = Counter()
        for c in kw.values():
            counts.update(c)
    else:
        counts = kw.get(sel_yr, Counter())
    top = counts.most_common(top_n)
    if not top:
        st.info("No keywords for that year yet.")
    else:
        st.caption(f"Most common words in titles of threads started in "
                   f"{'any year' if sel_yr == 'All-time' else sel_yr} "
                   "(setlist threads and common words excluded).")
        st.markdown("\n".join(
            f"""<div class="trow">
              <span class="meta">#{i}</span>
              <span style="flex:1;color:#e8e6e3;">{html.escape(word)}</span>
              <span class="cnt">{n:,}</span>
            </div>""" for i, (word, n) in enumerate(top, 1)),
            unsafe_allow_html=True)

c1, c2 = st.columns([3, 2])
term = c1.text_input("Search thread titles", placeholder="e.g. coventry, sphere, treason").strip()
sort = c2.selectbox("Sort", ["Most posts", "Least posts", "Newest", "Oldest", "Recently active",
                             "Longest-running", "Fastest growing", "Title A–Z"])
if _has_starter():
    user = st.text_input("Started by (username)",
                         placeholder="optional — e.g. someuser (partial matches ok)").strip()
else:
    user = ""

span_lo = int((meta.get("span_lo") or "2002")[:4])
span_hi = int((meta.get("span_hi") or str(datetime.date.today().year))[:4])
if span_hi > span_lo:
    yr_lo, yr_hi = st.slider("Year started", span_lo, span_hi, (span_lo, span_hi))
else:
    yr_lo, yr_hi = span_lo, span_hi
sc1, sc2, sc3 = st.columns(3)
setlists = sc1.checkbox("Include setlist threads", value=False)
big = sc2.checkbox("Include threads over 499", value=True)
min50 = sc3.checkbox("Only 50+ posts", value=False)

rows = _search(term, user, setlists, big, min50, sort, yr_lo, yr_hi)
if not rows:
    st.info("No threads match. Try a shorter or different term.")
else:
    st.caption(f"Showing {len(rows)} thread{'s' if len(rows) != 1 else ''}"
               + (" (capped at 150 — narrow your search for more)" if len(rows) == 150 else ""))
    # Render all rows in one markdown call — 150 separate st.markdown widgets made
    # every keystroke re-render the whole list, freezing the search box.
    blocks = []
    for subject, slug, tid, posts, first, last, starter in rows:
        url = f"{PT}/{tid}/{slug}" if tid else "#"
        lo, hi = (first or "")[:7], (last or "")[:7]
        span = lo if lo == hi else f"{lo} → {hi}".strip(" →")
        by = f'<span class="meta">by {html.escape(starter)}</span>' if starter else ""
        blocks.append(
            f"""<div class="trow">
              <a href="{url}" target="_blank">{html.escape(subject or '(untitled)')}</a>
              {by}
              <span class="meta">{span}</span>
              <span class="cnt">{(posts or 0):,}</span>
            </div>"""
        )
    st.markdown("\n".join(blocks), unsafe_allow_html=True)
