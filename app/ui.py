import os
import time

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
API_BASE = os.getenv("NETRAG_API_BASE", "http://127.0.0.1:8000")
REQUEST_TIMEOUT = int(os.getenv("NETRAG_UI_TIMEOUT", "180"))

st.set_page_config(
    page_title="Net-RAG — Network Protocol Assistant",
    page_icon="🛰️",
    layout="wide",
)

st.markdown(
    """
    <style>
      .netrag-hero {padding: 0.4rem 0 0.2rem 0;}
      .netrag-hero h1 {margin-bottom: 0.1rem; font-size: 2.0rem;}
      .netrag-sub {color: #7a8699; font-size: 0.95rem; margin-top: 0;}
      .chip {display:inline-block; padding:2px 10px; margin:2px 6px 2px 0;
             border-radius:999px; font-size:0.78rem; background:#1f2a3a; color:#cfe3ff;}
      .chip-warn {background:#3a2a1f; color:#ffd9a8;}
      .chip-ok {background:#1f3a2a; color:#b6f0c6;}
      .ctx-card {border:1px solid #2a3445; border-radius:10px; padding:0.4rem 0.8rem; margin-bottom:0.4rem;}
      .stTabs [data-baseweb="tab-list"] {gap: 4px;}
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


# ----- Session state -----
for key, default in {
    "ingest_job_id": None,
    "last_result": None,
    "last_query": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ----- Header -----
left, right = st.columns([0.74, 0.26])
with left:
    st.markdown(
        '<div class="netrag-hero"><h1>🛰️ Net-RAG</h1>'
        '<p class="netrag-sub">Grounded answers over RFCs, router/switch manuals, and architecture docs — '
        "hybrid retrieval (BM25 + dense) with verifiable citations.</p></div>",
        unsafe_allow_html=True,
    )
with right:
    health = api_health()
    if health is None:
        st.error(f"API offline\n\n`{API_BASE}`")
    else:
        jobs = health.get("ingest_jobs", {})
        worker = "up" if jobs.get("worker_alive") else "down"
        st.success(f"API online · v{health.get('version', '?') if isinstance(health, dict) else '?'}")
        st.caption(f"ingest worker: {worker} · queue: {jobs.get('queue_depth', 0)}")


# ----- Sidebar: ingestion -----
with st.sidebar:
    st.header("📥 Ingest documents")
    st.caption("Point at a folder of PDF / .md / .txt the **API process** can see.")

    quick = st.selectbox(
        "Quick paths",
        ["(custom)", "./sample_docs", "./docs/eval_corpus"],
        help="eval_corpus = small gold fixtures for the evaluation suite.",
    )
    default_path = "./sample_docs" if quick == "(custom)" else quick
    ingest_path = st.text_input("Docs folder path", value=default_path)

    ingest_mode = st.radio(
        "Mode",
        ["Background job (recommended)", "Sync (blocks)"],
        index=0,
        help="Background jobs queue on the API; one ingestion runs at a time (safe FAISS writes).",
    )

    if ingest_mode.startswith("Background"):
        if st.button("Queue ingestion job", use_container_width=True):
            try:
                resp = requests.post(
                    f"{API_BASE}/ingest/job",
                    json={"input_dir": ingest_path},
                    timeout=60,
                )
                if resp.ok:
                    st.session_state.ingest_job_id = resp.json()["job_id"]
                    st.rerun()
                else:
                    st.error(resp.text)
            except requests.RequestException as exc:
                st.error(f"API unreachable: {exc}")

        if st.session_state.ingest_job_id:
            jid = st.session_state.ingest_job_id
            try:
                sr = requests.get(f"{API_BASE}/ingest/status/{jid}", timeout=15)
            except requests.RequestException as exc:
                st.warning(f"Status poll failed: {exc}")
                sr = None

            if sr is not None and sr.ok:
                job = sr.json()["job"]
                pct = float(job.get("progress_percent") or 0) / 100.0
                st.progress(min(1.0, max(0.0, pct)))
                st.caption(f"**{job.get('stage', '')}** — {job.get('message', '')}")
                if job.get("current_file"):
                    st.caption(f"File: `{job['current_file']}`")
                jstate = job.get("state", "")
                if jstate == "succeeded":
                    st.success("Ingestion complete")
                    if job.get("result"):
                        st.json(job["result"])
                    st.session_state.ingest_job_id = None
                elif jstate == "failed":
                    st.error(job.get("error") or "Ingestion failed")
                    st.session_state.ingest_job_id = None
                elif jstate in ("queued", "running"):
                    time.sleep(0.8)
                    st.rerun()
                else:
                    st.caption(f"State: {jstate}")
            elif sr is not None:
                st.error(sr.text)
    else:
        if st.button("Run ingestion (sync)", use_container_width=True):
            with st.spinner("Building embeddings and FAISS index..."):
                try:
                    resp = requests.post(
                        f"{API_BASE}/ingest",
                        json={"input_dir": ingest_path},
                        timeout=600,
                    )
                    if resp.ok:
                        st.success("Ingestion complete")
                        st.json(resp.json()["result"])
                    else:
                        st.error(resp.text)
                except requests.RequestException as exc:
                    st.error(f"API unreachable: {exc}")

    st.divider()
    st.caption(
        "Tip: enable grounded LLM answers by setting `LLM_MODEL` and `LLM_API_KEY` "
        "in `.env` (otherwise Net-RAG returns retrieval-only results)."
    )


# ----- Main: ask -----
st.subheader("Ask a question")

EXAMPLES = [
    "Explain the TCP three-way handshake and the purpose of each segment.",
    "How does BGP route advertisement differ from OSPF link-state flooding?",
    "How long is the IPv6 base header and what fields does it contain?",
]
ex_cols = st.columns(len(EXAMPLES))
for i, ex in enumerate(EXAMPLES):
    if ex_cols[i].button(ex, key=f"ex_{i}", use_container_width=True):
        st.session_state.last_query = ex

query = st.text_area(
    "Your question",
    value=st.session_state.last_query,
    placeholder="e.g. What state transitions happen during a TCP handshake?",
    height=90,
)

c1, c2, c3 = st.columns([0.25, 0.4, 0.35])
top_k = c1.slider("Top K contexts", 1, 10, 5)
retrieval_pick = c2.selectbox(
    "Retrieval",
    ["Default (from .env)", "Dense only", "Hybrid BM25 + dense"],
    help="Hybrid fuses dense embeddings with BM25 lexical scores (RRF). Best for RFC numbers / exact terms.",
)
_retrieval_map = {
    "Default (from .env)": None,
    "Dense only": "dense",
    "Hybrid BM25 + dense": "hybrid",
}
retrieval_mode = _retrieval_map[retrieval_pick]
ask = c3.button("Ask Net-RAG", type="primary", use_container_width=True)


def render_result(result: dict) -> None:
    st.markdown("### Answer")
    st.markdown(result.get("answer", ""))

    # Metric chips
    chips = [f'<span class="chip">mode: {result.get("mode", "unknown")}</span>']
    ctxs = result.get("contexts") or []
    if ctxs and ctxs[0].get("metadata"):
        chips.append(
            f'<span class="chip">retrieval: {ctxs[0]["metadata"].get("retrieval_mode", "?")}</span>'
        )
    if "latency_ms" in result:
        chips.append(f'<span class="chip">total {result["latency_ms"]} ms</span>')
        if result.get("retrieval_ms") is not None:
            chips.append(f'<span class="chip">retrieval {result["retrieval_ms"]} ms</span>')
        if result.get("llm_ms") is not None:
            chips.append(f'<span class="chip">LLM {result["llm_ms"]} ms</span>')
    for cid in result.get("citations_used") or []:
        chips.append(f'<span class="chip chip-ok">{cid}</span>')
    usage = result.get("llm_usage")
    if usage:
        chips.append(
            f'<span class="chip">tokens {usage.get("total_tokens", "—")}</span>'
        )
    st.markdown(" ".join(chips), unsafe_allow_html=True)

    warns = result.get("warnings") or []
    if warns:
        with st.expander(f"⚠️ Warnings ({len(warns)})", expanded=False):
            for w in warns:
                st.markdown(f"- {w}")

    sources = result.get("sources") or []
    if sources:
        st.markdown("### Sources")
        st.markdown(" ".join(f'<span class="chip">{s}</span>' for s in sources), unsafe_allow_html=True)

    st.markdown("### Retrieved context")
    for idx, item in enumerate(ctxs, start=1):
        meta = item.get("metadata", {})
        citation_id = meta.get("citation_id", f"C{idx}")
        source_file = meta.get("source_file", "unknown")
        label = f"[{citation_id}] {source_file}"
        if meta.get("page") is not None:
            label += f" · p.{meta['page']}"
        if meta.get("section_hint"):
            sh = meta["section_hint"]
            label += f" · {sh[:53] + '…' if len(sh) > 56 else sh}"
        with st.expander(label):
            if meta.get("hybrid_rrf_score") is not None:
                st.caption(
                    f"dense_rank={meta.get('dense_rank')} · "
                    f"bm25_rank={meta.get('bm25_rank')} · rrf={meta.get('hybrid_rrf_score')}"
                )
            st.write(item.get("content", ""))


if ask:
    if not query.strip():
        st.warning("Enter a query first.")
    else:
        st.session_state.last_query = query
        with st.spinner("Retrieving context..."):
            body: dict = {"query": query, "top_k": top_k}
            if retrieval_mode is not None:
                body["retrieval_mode"] = retrieval_mode
            try:
                resp = requests.post(f"{API_BASE}/query", json=body, timeout=REQUEST_TIMEOUT)
            except requests.RequestException as exc:
                st.error(f"API unreachable: {exc}")
                resp = None

        if resp is not None and resp.ok:
            st.session_state.last_result = resp.json()["result"]
        elif resp is not None:
            st.error(resp.text)

if st.session_state.last_result:
    render_result(st.session_state.last_result)
