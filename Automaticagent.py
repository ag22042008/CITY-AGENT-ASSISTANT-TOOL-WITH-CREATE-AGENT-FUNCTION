#importing all libraries
from dotenv import load_dotenv
load_dotenv()
import os 
import requests
from rich import print
from langchain_mistralai import ChatMistralAI, data
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage,ToolMessage
from langchain.agents.middleware import wrap_tool_call
from tavily import TavilyClient
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
# creating tools
@tool
def get_weather(city:str)->str:
   "Get Current weather of a city"
   api_key=os.getenv("OPENWEATHER_API_KEY")
   url=f"http://api.openweathermap.org/data/2.5/weather?q={city},IN&appid={api_key}&units=metric"
   response=requests.get(url)
   data=response.json()
   if str(data.get("cod")) != "200":
      return f"Error: {data.get('message', 'Could not fetch weather')}"
   temp=data["main"]["temp"]
   desc=data["weather"][0]["description"]
   return f"weather in {city}:{desc}{temp}°C"

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
#TavilyNewstool

@tool
def get_news(city:str)->str:
   "Get the latest news about the city"
   response=tavily_client.search(
      query=f"""
Latest local news from {city}, UttarPradesh, India.
Exclude foreign cities.
Focus on local events, railways in{city},civic updates and business  in{city}.
""",
 time_range="week",
      search_depth="advanced",
      max_results=5
)
   results=response.get("results",[])

   if not results:
      return f"No news found for{city}"
   news_list = []
    
   for r in results:
        title = r.get("title", "No title")
        url = r.get("url", "")
        snippet = r.get("content", "")
        
        news_list.append(
            f"- {title}\n  🔗 {url}\n  📝 {snippet[:100]}..."
        )
    
   return f"Latest news in {city}:\n\n" + "\n\n".join(news_list)



llm=ChatMistralAI(model="mistral-small-2506")
@wrap_tool_call
def human_approval(request,handler):
    "Ask for human approc=val before every tool call"
    tool_name=request.tool_call["name"]
    confirm=input(f"Agent wants to call'{tool_name}'.Approve?(yes/no):")
    if confirm.lower()!="yes":
        return ToolMessage(
            content="tool call denied by user.",
            tool_call_id=request.tool_call["id"]
        )
    return handler(request)
agent=create_agent(
    llm,
    tools=[get_weather,get_aqi_detailed,get_news],
    system_prompt="you are a helpful city assistant",
    middleware=[human_approval]
)
print("=================city Agent===========")
print("type exit to quit")
while True:
    user_input=input("You: ")
    if user_input.lower()=="exit":
        break
    result=agent.invoke({
        "messages":[{"role":"user","content":user_input}]})
    print(result["messages"][-1].content)