import os
import time

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
API_BASE = os.getenv("NETRAG_API_BASE", "http://127.0.0.1:8000")
REQUEST_TIMEOUT = int(os.getenv("NETRAG_UI_TIMEOUT", "180"))
# Public/deployed mode hides owner-only ingestion controls (folder path, etc.).
PUBLIC_MODE = os.getenv("NETRAG_PUBLIC_MODE", "0").strip().lower() in ("1", "true", "yes")

st.set_page_config(
    page_title="Net-RAG",
    page_icon="N",
    layout="centered",
)

st.markdown(
    """
    <style>
      .block-container {max-width: 820px; padding-top: 2.2rem;}
      .netrag-sub {color: #8a93a6; font-size: 0.95rem; margin-top: -0.4rem;}
      .src-line {color: #8a93a6; font-size: 0.85rem; margin-top: 0.6rem;}
      .status-dot {font-size: 0.8rem; color: #8a93a6;}
    </style>
    """,
    unsafe_allow_html=True,
)


def api_health() -> dict | None:
    try:
        r = requests.get(f"{API_BASE}/health", params={"detailed": "true"}, timeout=5)
        if r.ok:
            return r.json()
    except requests.RequestException:
        return None
    return None


for key, default in {
    "ingest_job_id": None,
    "last_result": None,
    "last_query": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ---------------- Header ----------------
st.title("Net-RAG")
st.markdown(
    '<p class="netrag-sub">Ask questions about networking docs (RFCs, router manuals, '
    "architecture guides) and get answers backed by real sources.</p>",
    unsafe_allow_html=True,
)

health = api_health()
if health is None:
    st.error(f"Backend offline - start the API, then refresh. ({API_BASE})")
else:
    st.markdown('<span class="status-dot">online</span>', unsafe_allow_html=True)


# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Knowledge base")

    if PUBLIC_MODE:
        # Deployed demo: documents are preloaded; hide owner-only ingest controls.
        st.caption(
            "Preloaded with core networking references (TCP, BGP, OSPF, IPv6). "
            "Just ask a question on the right."
        )
    else:
        st.caption("Load the documents Net-RAG should answer from.")
        ingest_path = st.text_input("Folder path", value="./sample_docs")

        if st.button("Update knowledge base", use_container_width=True):
            try:
                resp = requests.post(
                    f"{API_BASE}/ingest/job", json={"input_dir": ingest_path}, timeout=60
                )
                if resp.ok:
                    st.session_state.ingest_job_id = resp.json()["job_id"]
                    st.rerun()
                else:
                    st.error(resp.text)
            except requests.RequestException as exc:
                st.error(f"Backend unreachable: {exc}")

        if st.session_state.ingest_job_id:
            jid = st.session_state.ingest_job_id
            try:
                sr = requests.get(f"{API_BASE}/ingest/status/{jid}", timeout=15)
            except requests.RequestException:
                sr = None
            if sr is not None and sr.ok:
                job = sr.json()["job"]
                pct = float(job.get("progress_percent") or 0) / 100.0
                st.progress(min(1.0, max(0.0, pct)), text=job.get("message", "Working..."))
                state = job.get("state", "")
                if state == "succeeded":
                    st.success("Knowledge base updated")
                    st.session_state.ingest_job_id = None
                elif state == "failed":
                    st.error(job.get("error") or "Update failed")
                    st.session_state.ingest_job_id = None
                elif state in ("queued", "running"):
                    time.sleep(0.8)
                    st.rerun()

    with st.expander("Advanced", expanded=False):
        top_k = st.slider("Passages to retrieve", 1, 10, 5)
        retrieval_pick = st.selectbox(
            "Search strategy",
            ["Automatic", "Semantic only", "Keyword + semantic"],
            help="Automatic uses the server default. Keyword + semantic (hybrid) is best "
            "for exact terms like RFC numbers.",
        )
        _retrieval_map = {
            "Automatic": None,
            "Semantic only": "dense",
            "Keyword + semantic": "hybrid",
        }
        retrieval_mode = _retrieval_map[retrieval_pick]


# ---------------- Main: ask ----------------
query = st.text_area(
    "Question",
    value=st.session_state.last_query,
    placeholder="e.g. Explain the TCP three-way handshake.",
    height=90,
    label_visibility="collapsed",
)
ask = st.button("Ask", type="primary", use_container_width=True)


def render_result(result: dict) -> None:
    mode = result.get("mode")
    ctxs = result.get("contexts") or []

    if mode == "retrieval_only" and ctxs:
        best = ctxs[0]
        meta = best.get("metadata", {})
        source = meta.get("source_file", "indexed document")
        text = (best.get("content") or "").strip()
        excerpt = text if len(text) <= 900 else text[:899] + "..."
        st.info(
            "Retrieval is working. Net-RAG found the best matching source passage. "
            "Open Evidence if you want to inspect the supporting text."
        )
        st.markdown(f"**Best match: {source}**")
        st.markdown(excerpt)
    else:
        st.markdown(result.get("answer", ""))

    if ctxs:
        with st.expander("Evidence"):
            sources = result.get("sources") or []
            if sources:
                st.caption(f"Sources: {', '.join(sources)}")
            for idx, item in enumerate(ctxs, start=1):
                meta = item.get("metadata", {})
                cid = meta.get("citation_id", f"C{idx}")
                src = meta.get("source_file", "unknown")
                label = f"{cid} - {src}"
                if meta.get("page") is not None:
                    label += f" - p.{meta['page']}"
                st.markdown(f"**{label}**")
                st.write(item.get("content", ""))
                st.divider()

    warns = result.get("warnings") or []
    details_bits = []
    if "latency_ms" in result:
        details_bits.append(f"Answered in {result['latency_ms']:.0f} ms")
    if result.get("mode"):
        details_bits.append(f"mode: {result['mode']}")
    if details_bits or warns:
        with st.expander("Details"):
            if details_bits:
                st.caption(" | ".join(details_bits))
            for w in warns:
                st.caption(w)


if ask:
    if not query.strip():
        st.warning("Type a question first.")
    else:
        st.session_state.last_query = query
        # Defaults if the Advanced panel was never opened this run.
        _top_k = locals().get("top_k", 5)
        _mode = locals().get("retrieval_mode", None)
        with st.spinner("Searching your documents..."):
            body: dict = {"query": query, "top_k": _top_k}
            if _mode is not None:
                body["retrieval_mode"] = _mode
            try:
                resp = requests.post(f"{API_BASE}/query", json=body, timeout=REQUEST_TIMEOUT)
            except requests.RequestException as exc:
                st.error(f"Backend unreachable: {exc}")
                resp = None
        if resp is not None and resp.ok:
            st.session_state.last_result = resp.json()["result"]
        elif resp is not None:
            st.error(resp.text)

if st.session_state.last_result:
    render_result(st.session_state.last_result)
