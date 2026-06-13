"""PT Wrapped — standalone public teaser app.

Reads the prebuilt aggregate DB (data/wrapped_<YEAR>.db, built by
pt_webapp/build_wrapped.py). No scraping, no raw post data.
Deep-linkable: ?user=<name> pre-loads a personal Wrapped.
"""
import streamlit as st
import plotly.graph_objects as go
import base64, datetime, html, json, os, sqlite3

YEAR = 2025
DB = os.path.join(os.path.dirname(__file__), "data", f"wrapped_{YEAR}.db")
MEDAL_COLORS = ["#ffd166", "#c0c0cc", "#cd7f32", "#8a8a96", "#8a8a96"]

st.set_page_config(page_title=f"PT Wrapped {YEAR}", page_icon="🌀", layout="centered")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&display=swap');
h1 {
    font-family: 'Space Grotesk', 'Segoe UI', sans-serif !important;
    background: linear-gradient(90deg, #ffd166, #ff8a3d, #ff5c8a, #9b8cff, #5ce0c0);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.5px;
}
.block-container { padding-top: 2.2rem; max-width: 760px; }

/* splashy tie-dye wash — palette pulled from the header photos */
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(620px at 12% 8%,  rgba(255, 138, 61, 0.16), transparent 65%),
        radial-gradient(540px at 88% 14%, rgba(124, 92, 255, 0.20), transparent 65%),
        radial-gradient(700px at 75% 75%, rgba(217, 43, 75, 0.13), transparent 65%),
        radial-gradient(520px at 18% 88%, rgba(92, 224, 192, 0.12), transparent 65%),
        radial-gradient(420px at 50% 45%, rgba(255, 209, 102, 0.07), transparent 65%),
        #0f0f14;
    background-attachment: fixed;
}
[data-testid="stHeader"] { background: transparent; }

.polaroids { display: flex; justify-content: center; gap: 6px; margin: 6px 0 18px; }
.polaroids img {
    height: 120px; width: auto; object-fit: cover;
    border: 5px solid #f2efe6; border-bottom-width: 16px; border-radius: 2px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.55);
    transform: rotate(-2deg);
    transition: transform 0.18s ease;
}
.polaroids img:hover { transform: rotate(0deg) scale(1.45); z-index: 10; }

/* WSP SUX Jerry — full-height column filling the right gutter */
.side-right {
    position: fixed; right: 0; top: 0; height: 100vh;
    width: min(calc((100vw - 820px) / 2), 480px);
    object-fit: cover; object-position: top center; z-index: 0; opacity: 0.94;
    border-left: 3px solid #26262f;
    box-shadow: -10px 0 30px rgba(0,0,0,0.5);
}
/* wrestler — big sticker filling the top-left gutter */
.corner-left {
    position: fixed; top: 16px; left: 12px;
    width: min(calc((100vw - 820px) / 2 - 18px), 470px);
    transform: rotate(-4deg); z-index: 0;
    border: 6px solid #f2efe6; border-bottom-width: 20px; border-radius: 2px;
    box-shadow: 0 10px 28px rgba(0,0,0,0.6);
}
@media (max-width: 1150px) { .side-right, .corner-left { display: none; } }
</style>""", unsafe_allow_html=True)


@st.cache_data
def _b64(name):
    p = os.path.join(os.path.dirname(__file__), "assets", f"{name}.jpg")
    if not os.path.exists(p):
        return None
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _img(name, cls):
    b64 = _b64(name)
    return (f'<img class="{cls}" src="data:image/jpeg;base64,{b64}" alt="">'
            if b64 else "")


def _polaroids():
    tag = _img("bigjerr", "")
    return f'<div class="polaroids">{tag}</div>' if tag else ""


def _card(title, value, sub="", accent="#9b8cff", big=False):
    size = "54px" if big else "38px"
    st.markdown(
        f"""<div style="background:linear-gradient(135deg,#16161e,#1b1b2a);
            border:1px solid #26262f;border-radius:16px;padding:24px 28px;margin:8px 0;">
          <div style="font-size:13px;letter-spacing:2px;text-transform:uppercase;color:{accent};">{title}</div>
          <div style="font-size:{size};font-weight:800;color:#e8e6e3;line-height:1.15;">{value}</div>
          <div style="font-size:15px;color:#8a8a96;margin-top:4px;">{sub}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def _fmt_day(iso):
    try:
        d = datetime.date.fromisoformat(iso)
        return f"{d.strftime('%B')} {d.day}"
    except (ValueError, TypeError):
        return iso or "—"


@st.cache_resource
def _db():
    return sqlite3.connect(DB, check_same_thread=False)


@st.cache_data(ttl=600)
def _meta():
    return dict(_db().execute("SELECT key, value FROM meta"))


@st.cache_data(ttl=600)
def _top_threads():
    # capped threads (all 499) rank by how fast they filled
    return _db().execute(
        "SELECT subject, posts, started, hours FROM top_threads "
        "ORDER BY posts DESC, COALESCE(hours, 1e9) ASC").fetchall()


def _fmt_span(hours):
    if hours < 48:
        h = int(hours)
        return f"{h}h {int((hours - h) * 60)}m"
    return f"{hours / 24:.1f} days"


def _fmt_days(days):
    return f"{days / 365.25:.1f} years" if days >= 365 else f"{days} days"


def _row(i, main, right, sub=""):
    color = MEDAL_COLORS[i] if i < 3 else "#8a8a96"
    sub_html = f'<span style="color:#8a8a96;font-size:13px;"> · {sub}</span>' if sub else ""
    st.markdown(
        f"""<div style="display:flex;align-items:center;gap:16px;background:#14141c;
            border:1px solid #26262f;border-radius:12px;padding:12px 18px;margin:6px 0;">
          <div style="font-size:22px;font-weight:800;color:{color};width:36px;">#{i+1}</div>
          <div style="flex:1;color:#e8e6e3;">{main}{sub_html}</div>
          <div style="color:#ff8a3d;font-weight:700;white-space:nowrap;">{right}</div>
        </div>""",
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=600)
def _table(sql):
    try:
        return _db().execute(sql).fetchall()
    except sqlite3.OperationalError:
        return []


@st.cache_data(ttl=600)
def _top_posters():
    return _db().execute(
        "SELECT username, posts FROM user_stats ORDER BY rank LIMIT 5").fetchall()


@st.cache_data(ttl=600)
def _user(name):
    row = _db().execute(
        "SELECT * FROM user_stats WHERE username = ? COLLATE NOCASE", (name,)).fetchone()
    if not row:
        return None
    cols = [c[1] for c in _db().execute("PRAGMA table_info(user_stats)")]
    return dict(zip(cols, row))


if not os.path.exists(DB):
    st.error("Aggregate database missing — run build_wrapped.py first.")
    st.stop()

meta = _meta()
total, unique = int(meta["total"]), int(meta["unique"])
n_posters = _db().execute("SELECT COUNT(*) FROM user_stats").fetchone()[0]

st.title(f"PT WRAPPED {YEAR}")
st.markdown(_img("wspsux", "side-right") + _img("wrestler", "corner-left")
            + _polaroids(), unsafe_allow_html=True)
st.caption("A year of Phantasy Tour, by the numbers. Type your handle for your personal Wrapped — "
           "then share the URL, it links straight to you.")

# ── Personal lookup (deep-linkable) ──────────────────────────────────────────
qp_user = st.query_params.get("user", "")
username = st.text_input("Your PT username", value=qp_user,
                         placeholder="e.g. yooser").strip()
if username:
    st.query_params["user"] = username
elif "user" in st.query_params:
    del st.query_params["user"]

if username:
    u = _user(username)
    if u is None:
        st.warning(f"No {YEAR} posts found for '{username}'. Check the spelling — "
                   "lurkers don't get a Wrapped.")
    else:
        uname = html.escape(u["username"])
        pct = u["rank"] / n_posters * 100
        _card(f"{uname}'s {YEAR}", f"{u['posts']:,} posts",
              f"#{u['rank']:,} of {n_posters:,} posters — top {max(pct, 0.1):.1f}%",
              accent="#ff5c8a", big=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            _card("Biggest day", _fmt_day(u["busiest_day"]),
                  f"{u['busiest_count']:,} posts", accent="#ff8a3d")
        with c2:
            _card("Longest streak", f"{u['streak']} days",
                  f"posted on {u['active_days']} days", accent="#5ce0c0")
        with c3:
            _card("Witching hour",
                  f"{u['peak_hour']:02d}:00" if u["peak_hour"] is not None else "—",
                  "your most common hour, Eastern time", accent="#4db8ff")
        c1, c2, c3 = st.columns(3)
        with c1:
            sub = (f"and started {u['threads_started']:,} of your own"
                   if u.get("threads_started") else "")
            _card("Threads touched", f"{u['threads_touched']:,}", sub, accent="#9b8cff")
        with c2:
            try:
                m = datetime.date.fromisoformat(u["peak_month"] + "-01").strftime("%B")
            except (ValueError, TypeError):
                m = u["peak_month"]
            _card("Your month", m, f"{u['peak_month_posts']:,} posts", accent="#ffd166")
        with c3:
            wk = u["weekend_pct"] or 0
            tag = ("posting is a weekend hobby" if wk >= 35
                   else "strictly a workday habit" if wk <= 15
                   else "of your posts hit on weekends")
            _card("Weekend share", f"{wk:.0f}%", tag, accent="#5ce0c0")

        c1, c2, c3 = st.columns(3)
        with c1:
            bd = _fmt_day(meta["busiest_day"])
            _card("On the board's biggest day", f"{u['big_day_posts']:,}",
                  f"posts from you on {bd}", accent="#ff8a3d")
        with c2:
            _card("Longest absence", f"{u['longest_absence']} days",
                  "your biggest break from PT", accent="#4db8ff")
        with c3:
            if u["prev_posts"]:
                delta = u["posts"] - u["prev_posts"]
                moved = (u["prev_rank"] - u["rank"]) if u["prev_rank"] else 0
                arrow = (f"up {moved} spots" if moved > 0
                         else f"down {abs(moved)} spots" if moved < 0 else "rank held")
                _card(f"vs {YEAR-1}", f"{delta:+,}", f"posts · {arrow}", accent="#ff5c8a")
            else:
                _card(f"vs {YEAR-1}", "—", f"no {YEAR-1} posts in local data",
                      accent="#ff5c8a")

        top5 = json.loads(u.get("top_threads") or "[]")
        flops = json.loads(u.get("flop_threads") or "[]")
        col_top, col_flop = st.columns(2)
        with col_top:
            if top5:
                st.markdown("##### Where you lived")
                share = top5[0][1] / u["posts"] * 100
                st.caption(f"Your #1 alone was {share:.0f}% of your year.")
                for subj, c in top5:
                    st.markdown(
                        f"""<div style="display:flex;gap:10px;background:#14141c;
                            border:1px solid #26262f;border-radius:10px;
                            padding:8px 14px;margin:5px 0;">
                          <div style="flex:1;color:#e8e6e3;font-size:14px;">{html.escape(subj or '?')}</div>
                          <div style="color:#9b8cff;font-weight:700;">{c:,}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
        with col_flop:
            if flops:
                st.markdown("##### Threads nobody came to")
                st.caption("You started them. The board shrugged.")
                for subj, pc in flops:
                    replies = max(pc - 1, 0)
                    label = "0 replies" if replies == 0 else f"{replies:,} replies"
                    st.markdown(
                        f"""<div style="display:flex;gap:10px;background:#14141c;
                            border:1px solid #26262f;border-radius:10px;
                            padding:8px 14px;margin:5px 0;">
                          <div style="flex:1;color:#e8e6e3;font-size:14px;">{html.escape(subj or '?')}</div>
                          <div style="color:#ff8a3d;font-weight:700;white-space:nowrap;">{label}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
        if u.get("top_started") and u.get("top_started_posts"):
            drew = ("hit the 499 cap" if u["top_started_posts"] >= 499
                    else f"drew {u['top_started_posts']:,} posts")
            _card("Best thread you started", html.escape(u["top_started"]),
                  drew, accent="#ffd166")

        hours = json.loads(u["hours"])
        if any(hours):
            fig = go.Figure(go.Bar(x=list(range(24)), y=hours,
                                   marker_color="#7c5cff", hoverinfo="skip"))
            fig.update_layout(
                height=180, margin=dict(l=10, r=10, t=30, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                title=dict(text="POSTING FINGERPRINT (EASTERN TIME)",
                           font=dict(size=11, color="#8a8a96")),
                xaxis=dict(tickvals=[0, 6, 12, 18, 23],
                           ticktext=["0h", "6h", "12h", "18h", "23h"],
                           color="#8a8a96", showgrid=False),
                yaxis=dict(visible=False), showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False})
        st.caption("Share your Wrapped: copy this page's URL — it links straight to you.")
    st.divider()

# ── Board recap ──────────────────────────────────────────────────────────────
st.markdown(f"## The board's {YEAR}")
st.caption("Everything below is board-wide — all of PT, not just you.")

st.markdown("#### The year in threads")
tt, cap_n = int(meta.get("threads_total", 0)), int(meta.get("capped_count", 0))
if tt:
    c1, c2 = st.columns(2)
    with c1:
        _card("Threads born", f"{tt:,}", f"new threads started in {YEAR}",
              accent="#9b8cff")
    with c2:
        _card("Hit the 499 cap", f"{cap_n:,}",
              f"{cap_n / tt * 100:.1f}% of new threads filled completely",
              accent="#ff8a3d")
starters = _table("SELECT username, threads FROM top_starters ORDER BY rank")
if starters:
    st.markdown("##### Most threads started")
    for i, (name, c) in enumerate(starters[:25]):
        _row(i, f"<b>{html.escape(name)}</b>", f"{c:,} threads")

c1, c2 = st.columns(2)
with c1:
    _card("Biggest day", _fmt_day(meta["busiest_day"]),
          f"{int(meta['busiest_count']):,} posts", accent="#ff8a3d")
with c2:
    prev = int(meta["prev_total"])
    yoy = f"{(total - prev) / prev * 100:+.0f}%" if prev else "—"
    _card("vs last year", yoy, f"{prev:,} posts in {YEAR-1}" if prev else "",
          accent="#4db8ff")

include_setlists = st.checkbox("Include setlist threads", value=False)


def _setlist_ok(subject):
    return include_setlists or "setlist" not in (subject or "").lower()


st.markdown("#### Fastest to 499")
st.caption("PT locks every thread at the cap — these hit it fastest.")
capped = sorted((t for t in _top_threads() if t[3] and _setlist_ok(t[0])),
                key=lambda t: t[3])
for i, (subject, c, started, hours) in enumerate(capped[:30]):
    _row(i, html.escape(subject or "(unknown)"), _fmt_span(hours),
         sub=f"started {started}")

if include_setlists:
    st.markdown("#### Biggest threads")
    st.caption("Setlist threads are exempt from the cap, so raw size means something here.")
    big = [t for t in _top_threads() if t[1] > 510 and _setlist_ok(t[0])]
    for i, (subject, c, started, hours) in enumerate(big[:15]):
        _row(i, html.escape(subject or "(unknown)"), f"{c:,} posts",
             sub=f"started {started}" if started else "")

    st.markdown("#### Biggest single days")
    st.caption("Most posts dumped into one thread in one calendar day.")
    days = [(s, d, c) for s, d, c in
            _table("SELECT subject, day, posts FROM thread_days ORDER BY rank")
            if c < 495 or "setlist" in (s or "").lower()]
    for i, (subject, day, c) in enumerate(days[:15]):
        _row(i, html.escape(subject or "(unknown)"), f"{c:,} posts", sub=day)

st.markdown("#### Highest Post Count")
cols = st.columns(5)
for i, ((name, c), col) in enumerate(zip(_top_posters(), cols)):
    with col:
        st.markdown(
            f"""<div style="text-align:center;background:#14141c;border:1px solid #26262f;
                border-radius:12px;padding:14px 6px;margin:6px 0;">
              <div style="font-size:20px;font-weight:800;color:{MEDAL_COLORS[i]};">#{i+1}</div>
              <div style="color:#e8e6e3;font-weight:600;overflow:hidden;text-overflow:ellipsis;
                   white-space:nowrap;">{html.escape(name)}</div>
              <div style="color:#8a8a96;font-size:13px;">{c:,}</div>
            </div>""",
            unsafe_allow_html=True,
        )

if int(meta["months_covered"]) < 12:
    st.caption(f"Data covers {meta['months_covered']}/12 months of {YEAR} so far.")
st.caption(f"Built from public PT data · {meta['built_at'][:10]}")
