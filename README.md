# PT Wrapped

Standalone public teaser for PT Analytics. Reads a prebuilt aggregate DB —
no scraping, no raw post data, no PT API calls at runtime.

## Build the data

From the main analytics project (needs its `data/posts.db` with full months):

```
cd ../pt_webapp
python build_wrapped.py 2025
```

Writes `data/wrapped_2025.db` here (a few MB). Re-run whenever more months land.

## Run locally

```
streamlit run app.py
```

## Deploy (Streamlit Community Cloud)

1. Push this directory as its own GitHub repo (include `data/wrapped_2025.db`).
2. share.streamlit.io → New app → pick the repo, main file `app.py`.
3. Share links: `https://<app-url>/?user=<pt-username>` deep-links a personal Wrapped.
