import os

import requests
import streamlit as st

API_BASE = os.getenv("NETRAG_API_BASE", "http://127.0.0.1:8000")

st.set_page_config(page_title="Net-RAG", layout="wide")
st.title("Net-RAG: Network Protocol & Architecture Assistant")

with st.sidebar:
    st.subheader("Ingest Documents")
    ingest_path = st.text_input(
        "Docs folder path",
        value="./sample_docs",
        help="Folder containing RFC/manual PDFs, .txt, or .md files",
    )
    if st.button("Run Ingestion"):
        with st.spinner("Building embeddings and FAISS index..."):
            resp = requests.post(
                f"{API_BASE}/ingest",
                json={"input_dir": ingest_path},
                timeout=120,
            )
            if resp.ok:
                st.success("Ingestion complete")
                st.json(resp.json()["result"])
            else:
                st.error(resp.text)

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
