import os
import time

import requests
import streamlit as st

API_BASE = os.getenv("NETRAG_API_BASE", "http://127.0.0.1:8000")

st.set_page_config(page_title="Net-RAG", layout="wide")
st.title("Net-RAG: Network Protocol & Architecture Assistant")

if "ingest_job_id" not in st.session_state:
    st.session_state.ingest_job_id = None

with st.sidebar:
    st.subheader("Ingest Documents")
    ingest_path = st.text_input(
        "Docs folder path",
        value="./sample_docs",
        help="Folder containing RFC/manual PDFs, .txt, or .md files",
    )
    ingest_mode = st.radio(
        "Ingest mode",
        [
            "Background job (recommended — Phase 3)",
            "Sync (blocks until complete)",
        ],
        index=0,
        help="Jobs queue on the API; one ingestion runs at a time per API instance (safe FAISS writes).",
    )

    if ingest_mode.startswith("Background"):
        if st.button("Queue ingestion job"):
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
        if st.button("Run Ingestion (sync)"):
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

st.subheader("Ask a Question")
query = st.text_area(
    "Example: Explain TCP 3-way handshake and what state transitions happen in each step."
)
top_k = st.slider("Top K Contexts", min_value=1, max_value=10, value=5)

if st.button("Ask Net-RAG", type="primary"):
    if not query.strip():
        st.warning("Enter a query first.")
    else:
        with st.spinner("Retrieving context..."):
            resp = requests.post(
                f"{API_BASE}/query",
                json={"query": query, "top_k": top_k},
                timeout=120,
            )
            if resp.ok:
                result = resp.json()["result"]
                st.markdown("### Answer")
                st.write(result["answer"])
                st.caption(f"Mode: {result.get('mode', 'unknown')}")
                if "latency_ms" in result:
                    cap_parts = [f"Total {result['latency_ms']} ms"]
                    if result.get("retrieval_ms") is not None:
                        cap_parts.append(f"retrieval {result['retrieval_ms']} ms")
                    if result.get("llm_ms") is not None:
                        cap_parts.append(f"LLM {result['llm_ms']} ms")
                    st.caption(" · ".join(cap_parts))
                    usage = result.get("llm_usage")
                    if usage:
                        st.caption(
                            f"Tokens — prompt: {usage.get('prompt_tokens', '—')}, "
                            f"completion: {usage.get('completion_tokens', '—')}, "
                            f"total: {usage.get('total_tokens', '—')}"
                        )
                cites = result.get("citations_used") or []
                if cites:
                    st.caption(f"Citations used in answer: {', '.join(cites)}")
                warns = result.get("warnings") or []
                if warns:
                    with st.expander("Warnings", expanded=False):
                        for w in warns:
                            st.markdown(f"- {w}")
                st.markdown("### Sources")
                st.write(result.get("sources", []))
                st.markdown("### Retrieved Context")
                for idx, item in enumerate(result.get("contexts", []), start=1):
                    meta = item["metadata"]
                    citation_id = meta.get("citation_id", f"C{idx}")
                    source_file = meta.get("source_file", "unknown")
                    label = f"[{citation_id}] {source_file}"
                    if meta.get("page") is not None:
                        label += f" · p.{meta['page']}"
                    if meta.get("section_hint"):
                        sh = meta["section_hint"]
                        if len(sh) > 56:
                            sh = sh[:53] + "…"
                        label += f" · {sh}"
                    with st.expander(label):
                        st.write(item["content"])
            else:
                st.error(resp.text)
