import os
import asyncio
import threading
import pickle
import warnings
from pathlib import Path
from dotenv import load_dotenv

import streamlit as st
import nest_asyncio


# LlamaIndex and Gemini setup
from llama_index.core import (
    Document, VectorStoreIndex, SummaryIndex,
    StorageContext, load_index_from_storage, Settings
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.tools import QueryEngineTool, FunctionTool
from llama_index.core.agent.workflow import FunctionAgent, ReActAgent
from llama_index.core.objects import ObjectIndex, ObjectRetriever
from llama_index.postprocessor.cohere_rerank import CohereRerank

import google.generativeai as genai
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

# Load environment
warnings.filterwarnings("ignore")
load_dotenv()

# Configure Google Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
llm = GoogleGenAI(model="gemini-2.5-flash", temperature=0)
embed_model = GoogleGenAIEmbedding(model_name="gemini-embedding-001", task_type="retrieval_document")
Settings.llm = llm
Settings.embed_model = embed_model

# Directories
DATA_DIR = Path("DATAN")
STORAGE_DIR = Path("storage")
SUMMARY_DIR = Path("summaries")
DATA_DIR.mkdir(exist_ok=True)
STORAGE_DIR.mkdir(exist_ok=True)
SUMMARY_DIR.mkdir(exist_ok=True)

# Event loop
event_loop = asyncio.new_event_loop()
asyncio.set_event_loop(event_loop)

class AsyncWorker(threading.Thread):
    def _init_(self, coro_fn, *args):
        super()._init_()
        self.coro_fn = coro_fn
        self.args = args
        self.result = None

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.result = loop.run_until_complete(self.coro_fn(*self.args))

# Build agent for single document
async def build_service_agent(doc: Document, base: str):
    base_folder = STORAGE_DIR / base
    vec_path = base_folder / "vector_index"
    sum_path = base_folder / "summary_index"
    summary_out = SUMMARY_DIR / f"{base}.pkl"
    vec_path.mkdir(parents=True, exist_ok=True)
    sum_path.mkdir(parents=True, exist_ok=True)

    # Vector index
    if (vec_path / "docstore.json").exists():
        vec_idx = load_index_from_storage(StorageContext.from_defaults(persist_dir=vec_path))
    else:
        nodes = SentenceSplitter().get_nodes_from_documents([doc])
        vec_idx = VectorStoreIndex(nodes, embed_model=embed_model)
        vec_idx.storage_context.persist(persist_dir=vec_path)

    # Summary index
    if (sum_path / "docstore.json").exists():
        sum_idx = load_index_from_storage(StorageContext.from_defaults(persist_dir=sum_path))
    else:
        nodes = SentenceSplitter().get_nodes_from_documents([doc])
        sum_idx = SummaryIndex(nodes)
        sum_idx.storage_context.persist(persist_dir=sum_path)

    vqe = vec_idx.as_query_engine(llm=llm)
    sqe = sum_idx.as_query_engine(llm=llm, response_mode="tree_summarize")

    if not summary_out.exists():
        s = await sqe.aquery("Summarize this Zone information to in 1–2 lines.")
        pickle.dump(str(s), open(summary_out, "wb"))
    summary = pickle.load(open(summary_out, "rb"))

    tools = [
        QueryEngineTool.from_defaults(query_engine=vqe, name=f"vector_{base}", description="semantic search in this Zone infromation"),
        QueryEngineTool.from_defaults(query_engine=sqe, name=f"summary_{base}", description="summarize this Zone infromation"),
    ]
    agent = FunctionAgent(tools=tools, llm=llm, system_prompt=f"You are specialized for {base} Zone Analysis. Use only tools.")
    return agent, summary

# Main agent builder
def init_agents():
    docs = []
    for file in DATA_DIR.glob("*.txt"):
        text = file.read_text(encoding='utf-8')
        docs.append(Document(text=text, metadata={"path": file.stem}))

    agents = {}
    summaries = {}
    for doc in docs:
        agent, summary = event_loop.run_until_complete(build_service_agent(doc, doc.metadata["path"]))
        agents[doc.metadata["path"]] = agent
        summaries[doc.metadata["path"]] = summary

    service_tools = []
    for base, agent in agents.items():
        async def q_fn(q, ag=agent): return str(await ag.run(q))
        service_tools.append(FunctionTool.from_defaults(q_fn, name=f"tool_{base}", description=summaries[base]))

    oi = ObjectIndex.from_objects(service_tools, index_cls=VectorStoreIndex, embed_model=embed_model)
    base_retr = oi.as_node_retriever(similarity_top_k=10)

    class CustomRetriever(ObjectRetriever):
        def retrieve(self, qb):
            nodes = base_retr.retrieve(qb)
            nodes = CohereRerank(top_n=5, model="rerank-v3.5").postprocess_nodes(nodes, qb)
            tools = [oi.object_node_mapping.from_node(n.node) for n in nodes]
            sub = FunctionAgent(name="compare_tool", tools=tools, llm=llm, system_prompt="Compare multiple Zone infromation; use tools only.")
            async def comp(q): return str(await sub.run(q))
            tools.append(FunctionTool.from_defaults(comp, name="compare_tool", description="Compare Zone infromation"))
            return tools

    top_agent = ReActAgent(tool_retriever=CustomRetriever(base_retr, oi.object_node_mapping), llm=llm, system_prompt="You are a UDS expert. Use tools only.")
   

    return top_agent

# Streamlit UI
st.set_page_config(page_title="Chatbot", layout="wide")
st.title("🚗 Emergency Chatbot")

# File uploader
uploaded_files = st.file_uploader("📁 Upload Zone details .txt files", type=["txt"], accept_multiple_files=True)
if uploaded_files:
    for uf in uploaded_files:
        out_path = DATA_DIR / uf.name
        with open(out_path, "wb") as f:
            f.write(uf.getvalue())
    st.success("✅ Files uploaded! Click 'Initialize Services' to build agents.")

# Initialize button
if st.button("Initialize Services"):
    with st.spinner("🔧 Building indices and agents..."):
        top_agent = init_agents()
        st.session_state["top_agent"] = top_agent
        st.session_state["history"] = []
    st.success("✅ Initialization complete!")

# Chat Interface
if "top_agent" in st.session_state:

    nest_asyncio.apply()

    async def query_agents(query):
        res1 = await st.session_state["top_agent"].run(query)
        await asyncio.sleep(1)
        return res1

    # Chat input
    query = st.chat_input("💬 Ask about UDS services...")

    if query:
        st.session_state["history"].append(("user", query))
        res1 = event_loop.run_until_complete(query_agents(query))
        st.session_state["history"].append(("top_agent", res1))
       

    # Display history
    for sender, msg in st.session_state["history"]:
        if sender == "user":
            with st.chat_message("user"):
                st.markdown(msg)
        elif sender == "top_agent":
            with st.chat_message("assistant"):
                st.markdown(f"🔹 *TopAgent (Multi-agent reasoning):*\n\n{msg}")
        elif sender == "baseline":
            with st.chat_message("assistant"):
                st.markdown(f"🔸 *Baseline RAG:*\n\n{msg}")

else:
    st.info("⬆ Please upload files and initialize services to start chatting.")