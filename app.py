"""
City Assistant — Streamlit UI
------------------------------
A chat UI for the LangChain/LangGraph city agent with:
  - Weather (OpenWeather)
  - AQI + pollutant breakdown (OpenWeather)
  - Local news with links (Tavily)
  - Human-in-the-loop approval before every tool call

All tool logic is unchanged from the original script, except get_news(),
which now returns ONLY headlines + links (no extra snippets/keyword focus).
"""

import os
import uuid

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Streamlit Community Cloud doesn't read .env files -- keys set via
# "Settings -> Secrets" only land in st.secrets, not os.environ.
# Mirror them into the environment so os.getenv(...) works the same
# way locally (.env) and on Cloud (st.secrets).
for _key in ("MISTRAL_API_KEY", "OPENWEATHER_API_KEY", "TAVILY_API_KEY"):
    if not os.getenv(_key):
        try:
            if _key in st.secrets:
                os.environ[_key] = st.secrets[_key]
        except Exception:
            pass  # no secrets.toml present (e.g. running purely from .env)

from langchain_core.messages import ToolMessage
from langchain.tools import tool
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from langchain_mistralai import ChatMistralAI
from tavily import TavilyClient


# ----------------------------------------------------------------------
# Tools  (weather + AQI logic untouched — only get_news was simplified)
# ----------------------------------------------------------------------

@tool
def get_weather(city: str) -> str:
    "Get current weather of a city"
    api_key = os.getenv("OPENWEATHER_API_KEY")
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city},IN&appid={api_key}&units=metric"
    response = requests.get(url)
    data = response.json()
    if str(data.get("cod")) != "200":
        return f"Error: {data.get('message', 'Could not fetch weather')}"
    temp = data["main"]["temp"]
    desc = data["weather"][0]["description"]
    return f"weather in {city}:{desc} {temp}°C"


@tool
def get_aqi_detailed(city: str) -> str:
    "Get current AQI and pollutant breakdown (PM2.5, PM10, etc.) of a city"
    api_key = os.getenv("OPENWEATHER_API_KEY")
    geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city},IN&limit=1&appid={api_key}"
    geo_data = requests.get(geo_url).json()

    if not geo_data:
        return f"Error: Could not find city '{city}'"

    lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]

    aqi_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={api_key}"
    data = requests.get(aqi_url).json()
    if "list" not in data or not data["list"]:
        return f"Error: Could not fetch AQI for {city}"
    entry = data["list"][0]
    aqi_index = entry["main"]["aqi"]
    aqi_labels = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}
    category = aqi_labels.get(aqi_index, "Unknown")

    c = entry["components"]

    return (
        f"AQI in {city}: {aqi_index} ({category}) | "
        f"PM2.5: {c['pm2_5']} µg/m³, PM10: {c['pm10']} µg/m³, "
        f"O3: {c['o3']} µg/m³, NO2: {c['no2']} µg/m³"
    )


tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


@tool
def get_news(city: str) -> str:
    "Get the latest news headlines and links for a city"
    response = tavily_client.search(
        query=f"Latest news from {city}, Uttar Pradesh, India",
        time_range="week",
        search_depth="advanced",
        max_results=5,
    )
    results = response.get("results", [])

    if not results:
        return f"No news found for {city}"

    news_list = []
    for r in results:
        title = r.get("title", "No title")
        url = r.get("url", "")
        news_list.append(f"- [{title}]({url})")

    return f"Latest news in {city}:\n\n" + "\n".join(news_list)


# ----------------------------------------------------------------------
# Human-in-the-loop approval middleware (same intent as the CLI version,
# rebuilt on LangGraph's interrupt()/Command(resume=...) so it works in
# a request/response web UI instead of blocking on input()).
# ----------------------------------------------------------------------

@wrap_tool_call
def human_approval(request, handler):
    "Ask for human approval before every tool call"
    decision = interrupt(
        {
            "tool_name": request.tool_call["name"],
            "tool_args": request.tool_call["args"],
        }
    )
    if decision != "yes":
        return ToolMessage(
            content="Tool call denied by user.",
            tool_call_id=request.tool_call["id"],
        )
    return handler(request)


# ----------------------------------------------------------------------
# Streamlit page setup
# ----------------------------------------------------------------------

st.set_page_config(page_title="City Assistant", page_icon="🏙️", layout="centered")

st.markdown(
    """
    <style>
    .stChatMessage { border-radius: 12px; }
    .approval-box {
        border: 1px solid #e0a800;
        background-color: #fff8e1;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🏙️ City Assistant")
st.caption("Weather • Air Quality • Local News — powered by Mistral + LangGraph")

# ----------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------

if "agent" not in st.session_state:
    llm = ChatMistralAI(model="mistral-small-latest")
    st.session_state.agent = create_agent(
        llm,
        tools=[get_weather, get_aqi_detailed, get_news],
        system_prompt="you are a helpful city assistant",
        middleware=[human_approval],
        checkpointer=MemorySaver(),
    )

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending" not in st.session_state:
    st.session_state.pending = None  # holds the interrupted tool-call info


def handle_agent_result(result):
    """Store an assistant reply, or capture a pending tool approval."""
    if isinstance(result, dict) and "__interrupt__" in result:
        st.session_state.pending = result["__interrupt__"][0].value
    else:
        final = result["messages"][-1].content
        st.session_state.messages.append({"role": "assistant", "content": final})


# ----------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️ Setup status")
    st.write("Mistral API key:", "✅" if os.getenv("MISTRAL_API_KEY") else "❌ missing")
    st.write("OpenWeather API key:", "✅" if os.getenv("OPENWEATHER_API_KEY") else "❌ missing")
    st.write("Tavily API key:", "✅" if os.getenv("TAVILY_API_KEY") else "❌ missing")

    st.divider()
    st.header("🧰 Tools")
    st.markdown("- 🌤️ **get_weather** — current weather\n"
                "- 🫁 **get_aqi_detailed** — AQI + pollutants\n"
                "- 📰 **get_news** — headlines + links")

    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending = None
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()

# ----------------------------------------------------------------------
# Chat history
# ----------------------------------------------------------------------

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

config = {"configurable": {"thread_id": st.session_state.thread_id}}

# ----------------------------------------------------------------------
# Pending tool-call approval UI
# ----------------------------------------------------------------------

if st.session_state.pending:
    info = st.session_state.pending
    with st.chat_message("assistant"):
        st.markdown(
            f"""<div class="approval-box">
            🔧 The agent wants to call <b>{info['tool_name']}</b>
            with arguments <code>{info['tool_args']}</code>.<br>Approve this action?
            </div>""",
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        approve = col1.button("✅ Approve", use_container_width=True, key="approve_btn")
        deny = col2.button("🚫 Deny", use_container_width=True, key="deny_btn")

    if approve or deny:
        decision = "yes" if approve else "no"
        st.session_state.pending = None
        result = st.session_state.agent.invoke(Command(resume=decision), config=config)
        handle_agent_result(result)
        st.rerun()

    st.stop()  # wait for the user's decision before accepting new chat input

# ----------------------------------------------------------------------
# Chat input
# ----------------------------------------------------------------------

user_input = st.chat_input("Ask about weather, AQI, or news in a city...")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.spinner("Thinking..."):
        result = st.session_state.agent.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
        )
    handle_agent_result(result)
    st.rerun()
