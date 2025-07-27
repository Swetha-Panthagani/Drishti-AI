import sys
import os
import json
import concurrent.futures
from google import genai
from google.genai.types import HttpOptions, Part
import re
import asyncio
from flask import Flask, render_template, request, jsonify

# agent for chat
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types


import warnings
warnings.filterwarnings("ignore")

# Add the virtual environment's site-packages to the Python path
venv_path = os.path.join(os.path.dirname(__file__), '.venv', 'lib', 'python' + sys.version[:3], 'site-packages')
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)


app = Flask(__name__, template_folder='templates') # Ensure template_folder is set

# Define video_uris globally
video_uris = {
    "Zone_A": "gs://video_bucket_11212/ZoneA.mp4",
    "Zone_B": "gs://video_bucket_11212/ZoneB.mp4",
    "Zone_C": "gs://video_bucket_11212/ZoneC.mp4",
    "Zone_D": "gs://video_bucket_11212/ZoneD.mp4",
}




# Define the shared prompt for video analysis
PROMPT = (
    "This video shows a specific zone of a public event. "
    "Estimate the number of people in the frame, and rate the crowd density on a scale of 1 to 10 "
    "(1 being empty, 10 being extremely packed). Also mention whether the movement of the crowd is smooth or stagnant. "
    "Additionally, observe and report any **anomalies beyond crowd counts**, such as signs of smoke, fire, or the visual signature "
    "of a panicked crowd surge. If any such anomaly is detected, clearly flag it as a **HIGH-PRIORITY ALERT** and describe the nature of the threat."
)

# Function to analyze a single video
def analyze_video(zone_id, video_uri):
    try:
        client = genai.Client(http_options=HttpOptions(api_version="v1"))

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                Part.from_uri(file_uri=video_uri, mime_type="video/mp4"),
                PROMPT,
            ],
        )
        return {zone_id: response.text}
    except Exception as e:
        return {zone_id: f"Error: {str(e)}"}

# Run analysis in parallel
def analyze_all_zones(video_map):
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_zone = {
            executor.submit(analyze_video, zone, uri): zone
            for zone, uri in video_map.items()
        }
        for future in concurrent.futures.as_completed(future_to_zone):
            zone = future_to_zone[future]
            try:
                result = future.result()
                results.update(result)
            except Exception as exc:
                results[zone] = f"Error: {str(exc)}"
    return results

# Agent for heatmap and chatbot
main_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="MainAgent",
    instruction="""
You are an intelligent safety and crowd management agent at a public event. You will receive zone summaries as context. Your primary function is to respond to specific queries based ONLY on this context.

1.  **If the user query is EXACTLY 'GENERATE_HEATMAP_STATUS'**:
    You MUST analyze the context and respond ONLY with a Python dictionary assigning a severity level to each zone.
    - **Green Zone**: Crowd density is 5 or below, movement is smooth, and no anomalies are detected.
    - **Yellow Zone**: Crowd density is 6 or 7, but movement is smooth, and no anomalies are detected.
    - **Red Zone**: Crowd density is 8 or 10, or if any **anomalies** such as smoke, fire, or signs of panic are present.
    Your output must be in this format and nothing else:
    ```python
    {
        "Zone_A": "Green",
        "Zone_B": "Yellow",
        "Zone_C": "Red",
        "Zone_D": "Green"
    }
    ```

""",
)

# Agent session management
session_service = InMemorySessionService()
APP_NAME = "chat_bot_agent"
USER_ID = "user_1"
SESSION_ID = "session_001"

# Define Agent Interaction Function
async def call_agent_async(query: str, user_id: str, session_id: str, zone_context_str: str = ""):
    session = await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    runner = Runner(
        agent=main_agent, app_name=APP_NAME, session_service=session_service
    )
    
    combined_message = f"CONTEXT:{zone_context_str} QUERY:{query}"
    content = types.Content(role='user', parts=[types.Part(text=combined_message)])
    
    final_response_text = "Agent did not produce a final response."
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response_text = event.content.parts[0].text
            elif event.actions and event.actions.escalate:
                final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
            break
    return final_response_text

@app.route("/")
def index():
    attendees = 123
    os.environ["GOOGLE_CLOUD_PROJECT"] = "ace-well-467010-f5"
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"ace-well-467010-f5-7cf97226dec2.json"

    zone_summery = analyze_all_zones(video_uris)
    zone_summery_str = str(zone_summery)
    
    agent_output = asyncio.run(call_agent_async("GENERATE_HEATMAP_STATUS", USER_ID, SESSION_ID, zone_summery_str))
    
    zone_status = {}
    match = re.search(r"```python(.*?)```", agent_output, re.DOTALL)
    if match:
        json_string = match.group(1).strip()
        try:
            zone_status = json.loads(json_string)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from agent output for heatmap: {e}")
            print(f"Agent output for heatmap: {agent_output}")

    zone_A_summary = zone_summery.get('Zone_A', 'N/A')
    zone_B_summary = zone_summery.get('Zone_B', 'N/A')
    zone_C_summary = zone_summery.get('Zone_C', 'N/A')
    zone_D_summary = zone_summery.get('Zone_D', 'N/A')

    heatmap_zoneA = zone_status.get("Zone_A", "Unknown")
    heatmap_zoneB = zone_status.get("Zone_B", "Unknown")
    heatmap_zoneC = zone_status.get("Zone_C", "Unknown")
    heatmap_zoneD = zone_status.get("Zone_D", "Unknown")

    return render_template(
        'index.html',
        attendees=attendees,
        zone_A=zone_A_summary,
        zone_B=zone_B_summary,
        zone_C=zone_C_summary,
        zone_D=zone_D_summary,
        heatmap_zoneA=heatmap_zoneA,
        heatmap_zoneB=heatmap_zoneB,
        heatmap_zoneC=heatmap_zoneC,
        heatmap_zoneD=heatmap_zoneD,
        zone_results=zone_summery,
        zone_summery_str=zone_summery_str
    )

@app.route("/chatbot", methods=["POST"])
async def chatbot():
    data = request.get_json()
    user_message = data.get("message")
    zone_context = data.get("context")

    if not user_message or zone_context is None:
        return jsonify({"error": "Missing message or context"}), 400

    agent_response = await call_agent_async(user_message, USER_ID, SESSION_ID, zone_context)
    return jsonify({"response": agent_response})

def main():
    app.run(port=int(os.environ.get('PORT', 80)))

if __name__ == "__main__":
    main()
