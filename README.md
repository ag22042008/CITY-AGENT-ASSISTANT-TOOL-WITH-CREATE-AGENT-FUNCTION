# 🏙️ City Assistant — Streamlit UI

A chat-based UI for your LangChain/LangGraph city agent (weather, AQI, local news),
with human-in-the-loop approval before every tool call.

## What changed vs. your original script

- **UI**: replaced the terminal `while True / input()` loop with a Streamlit chat app
  (`app.py`) — sidebar status panel, chat bubbles, and clickable Approve/Deny buttons
  instead of typing `yes`/`no` into a console prompt.
- **Human approval**: same intent as your `human_approval` middleware, but rebuilt on
  LangGraph's `interrupt()` / `Command(resume=...)` so it can pause mid-run and wait
  for a button click in the browser (a blocking `input()` doesn't work in a web app).
- **`get_news`**: simplified to return **only headlines + clickable links** — the
  civic/railway/business keyword-stuffing and content snippets were removed, per your
  request. `get_weather` and `get_aqi_detailed` are untouched.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in your real API keys
streamlit run app.py
```

## Using it

1. Type a question like *"What's the weather and AQI in Noida?"* in the chat box.
2. Whenever the agent wants to call a tool, an approval card appears — click
   **✅ Approve** or **🚫 Deny**.
3. Use **🗑️ Clear conversation** in the sidebar to start a fresh thread.

## Notes

- The sidebar shows ✅/❌ for each required API key (Mistral, OpenWeather, Tavily) so
  you can quickly spot a missing `.env` value.
- Conversation state is kept per Streamlit session via a LangGraph `MemorySaver`
  checkpointer, keyed by a random `thread_id` — refreshing the page (or hitting
  "Clear conversation") starts a new thread.
