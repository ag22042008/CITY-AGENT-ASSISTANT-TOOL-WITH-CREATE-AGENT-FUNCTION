# 🏙️ City Assistant —

A chat-based Streamlit UI for a LangChain/LangGraph city assistant that can answer questions about weather, AQI, and local news — with human approval required before every tool call.

## Overview

This project replaces a terminal-based agent flow with a browser-based chat experience. Instead of using `input()` in the console, the assistant now runs inside Streamlit with chat bubbles, a sidebar status panel, and Approve/Deny buttons for tool execution.

It is designed to keep the user in control while still allowing the agent to reason and act with external tools when needed.

## Features

* Streamlit chat interface for natural conversation
* Human-in-the-loop approval before every tool call
* LangGraph `interrupt()` and `Command(resume=...)` support for browser-based pausing
* Sidebar API key status indicators
* Conversation memory per session using `MemorySaver`
* Clear conversation button to reset the thread
* Simplified news tool output: headlines + clickable links only

## What changed from the original script

* **UI upgrade**: replaced the terminal `while True / input()` loop with a Streamlit app in `app.py`
* **Approval flow**: replaced console-based approval with browser buttons using LangGraph interruption and resume support
* **News tool update**: `get_news` now returns only headlines and clickable links, with extra keyword-stuffing and content snippets removed
* **Unchanged tools**: `get_weather` and `get_aqi_detailed` remain the same

## Tech Stack

* Python
* Streamlit
* LangChain
* LangGraph
* Tavily
* OpenWeather
* Mistral
* MemorySaver checkpointing

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# fill in your real API keys
streamlit run app.py
```

## Required Environment Variables

Make sure your `.env` file includes the required API keys for:

* Mistral
* OpenWeather
* Tavily

The sidebar in the app shows a quick ✅ / ❌ status for each key so missing values are easy to spot.

## Usage

1. Start the app.
2. Ask a question like:
   `What's the weather and AQI in Noida?`
3. When the agent wants to call a tool, an approval card appears.
4. Click **✅ Approve** or **🚫 Deny**.
5. Use **🗑️ Clear conversation** in the sidebar to start a fresh thread.

## Conversation State

Conversation state is stored per Streamlit session using a LangGraph `MemorySaver` checkpointer. Each session is keyed by a random `thread_id`, so refreshing the page or clearing the conversation starts a new thread.

## Repository

GitHub: [CITY-AGENT-ASSISTANT-TOOL-WITH-CREATE-AGENT-FUNCTION](https://github.com/ag22042008/CITY-AGENT-ASSISTANT-TOOL-WITH-CREATE-AGENT-FUNCTION)

## Project Goal

The goal of this assistant is to provide a simple, safe, and interactive city information assistant that can answer location-based questions while keeping the user in control of every external action.
