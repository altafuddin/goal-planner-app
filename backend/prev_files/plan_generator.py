# planner_logic.py
import os
import datetime
import json
import re

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import google.generativeai as genai
from dotenv import load_dotenv  #gemini
# Ensure you have a .env file with GOOGLE_API_KEY set

load_dotenv() # Load environment variables from .env file

class SkillLearningPlanner: # Renamed for clarity, or keep SkillLearningPlannerChat
    def __init__(self):
        # Load GOOGLE_API_KEY from environment variables
        # The hardcoded key should be removed and placed in .env
        # Example .env file content:
        # GOOGLE_API_KEY="AIzaSyB_OeDe3_rqv4JwRbFhYUnQ6-8co3R9aIs"

        google_api_key_env = os.environ.get("GOOGLE_API_KEY")
        if not google_api_key_env:
            print("FATAL: GOOGLE_API_KEY environment variable not set. Exiting.")
            # In a real app, you might raise an exception or handle this more gracefully
            # For FastAPI, the app might fail to start if critical configs are missing.
            raise ValueError("GOOGLE_API_KEY not found in environment variables.")
        
        genai.configure(api_key=google_api_key_env)

        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        # OAuth credential handling:
        # For FastAPI, especially when deployed, the initial `run_local_server`
        # part of OAuth can be tricky.
        # Recommendation for local dev: Run your original script once to generate `token.json`.
        # The FastAPI app can then use this `token.json`.
        # For production: Use a service account or a pre-authorized refresh token stored securely.
        self.creds = self._get_oauth_credentials()
        self.calendar_service = build('calendar', 'v3', credentials=self.creds)
        # Chat history per request might be better, or manage sessions if needed.
        # For now, a single chat instance might mix contexts if multiple users hit it.
        # Let's keep it simple for MVP, assuming one "session" at a time or stateless plan generation.
        # self.chat = self.model.start_chat(history=[]) # Removed global chat history for statelessness

    def _get_oauth_credentials(self): # Renamed to be an internal method
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    print("Refreshing OAuth token...")
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}. Re-authenticating (manual step may be needed).")
                    # In a server environment, automatic re-authentication via browser flow is not feasible.
                    # This part would need to be handled by an initial manual auth or service account.
                    if os.path.exists('token.json'): os.remove('token.json')
                    # For FastAPI, avoid run_local_server here.
                    # Assume credentials.json is present for an initial manual setup if token.json is bad.
                    print("Attempting to use credentials.json for a new token (requires manual intervention if it opens a browser)")
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', self.SCOPES)
                    creds = flow.run_local_server(port=0) # This will block if run inside a FastAPI request. Best done offline.
            else:
                # This flow should ideally be run once manually to get token.json
                print("No valid token.json. Attempting to create one using credentials.json (manual intervention may be needed if it opens a browser)")
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0) # This will block.
            
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
            print("OAuth token updated/created.")
        return creds

    def _extract_valid_json(self, response_text): # Renamed
        try:
            # Simplified extraction: look for the outermost JSON
            match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                # Fallback: find first '{' and last '}'
                start_index = response_text.find("{")
                end_index = response_text.rfind("}")
                if start_index == -1 or end_index == -1 or end_index < start_index:
                    print("Warning: No clear JSON object found in the response.")
                    return None
                json_str = response_text[start_index:end_index + 1]

            # Basic cleaning (remove trailing commas before '}' or ']')
            json_str = re.sub(r',\s*(\}|\])', r'\1', json_str)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            print(f"Problematic JSON string: {json_str if 'json_str' in locals() else response_text[:500]}")
            return None
        except Exception as e:
            print(f"General Error during JSON extraction: {e}")
            return None

    def _parse_preferred_time_to_datetime(self, preferred_time_str: str) -> datetime.time:
        """ Parses a flexible time string (e.g., "9 AM", "14:30", "evening") into a datetime.time object. """
        hours, minutes = 9, 0 # Default if parsing fails 
        try:
            time_match = re.search(r'(\d{1,2})(?:[:.](\d{1,2}))?\s*(am|pm)?', preferred_time_str, re.IGNORECASE)
            if time_match:
                hr_part = int(time_match.group(1))
                min_part = time_match.group(2)
                ampm_part = (time_match.group(3) or '').lower()
                minutes = int(min_part) if min_part else 0

                if ampm_part == 'pm' and hr_part < 12: hours = hr_part + 12
                elif ampm_part == 'am' and hr_part == 12: hours = 0 # 12 AM is midnight
                elif not ampm_part and hr_part >= 0 and hr_part < 24 : hours = hr_part # Assume 24h if no AM/PM
                elif ampm_part == 'am' and hr_part > 0 and hr_part < 12: hours = hr_part
                else: hours = hr_part # direct hour if no am/pm (e.g. 14 for 2pm)

                if not (0 <= hours <= 23 and 0 <= minutes <= 59): # Basic validation
                    print(f"Warning: Parsed time {hours}:{minutes} is invalid. Defaulting.")
                    hours, minutes = 9,0


            elif "morning" in preferred_time_str.lower(): hours = 9
            elif "afternoon" in preferred_time_str.lower(): hours = 14
            elif "evening" in preferred_time_str.lower() or "night" in preferred_time_str.lower(): hours = 19
            else:
                print(f"Warning: Could not parse preferred time '{preferred_time_str}'. Defaulting to 09:00.")
        except Exception as e:
            print(f"Error parsing preferred time '{preferred_time_str}': {e}. Defaulting to 09:00.")
        return datetime.time(hours, minutes)

    def generate_and_structure_plan(self, skill: str, duration_days: int, start_date_str: str,
                                    learning_style: str = None, preferred_time_str: str = "9 AM",
                                    daily_hours: float = 2.0):
        prompt_parts = [
            f"Generate a detailed {duration_days}-day learning plan for mastering {skill}."
        ]
        start_date_obj = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        
        prompt_parts.append(f"The plan should include: daily learning objectives, practical projects/exercises, and estimated time commitment per day. Dates should be in ISO format (YYYY-MM-DD), starting from {start_date_obj.strftime('%Y-%m-%d')}.")

        if learning_style: prompt_parts.append(f"Consider a {learning_style} learning style.")
        if preferred_time_str: prompt_parts.append(f"Each day's activities should ideally be scheduled around {preferred_time_str}.")
        if daily_hours: prompt_parts.append(f"The total daily commitment should be around {daily_hours} hours.")

        prompt_parts.append(
            "Format the output as a structured JSON. The JSON should have a top level key named 'learningPlan' "
            "which contains a list of daily entries. Each daily entry must have 'dayNumber' (int), "
            "'date' (ISO format YYYY-MM-DD), 'objective' (string), 'projects_exercises' (string), "
            "and 'estimated_time_hours' (float or int). Do not include any comments or extra text outside the JSON. "
            "Ensure all dates in the plan strictly follow the YYYY-MM-DD format."
        )
        
        prompt = "\n".join(prompt_parts)
        print("\nSending prompt to AI...")
        try:
            # For stateless plan generation, start a new chat each time or use generate_content
            response = self.model.generate_content(prompt) # Changed from self.chat.send_message
            response_text = response.text.strip()
            raw_plan_json = self._extract_valid_json(response_text)

            if not raw_plan_json or "learningPlan" not in raw_plan_json:
                return None, "Failed to parse valid plan from AI response."

            # Now, structure this into the Task format with start/end times
            structured_tasks_for_api = []
            human_readable_parts = []
            
            preferred_time_dt = self._parse_preferred_time_to_datetime(preferred_time_str)

            for day_data in raw_plan_json.get("learningPlan", []):
                try:
                    task_date_str = day_data.get("date")
                    if not task_date_str: continue # Skip if no date

                    task_date_obj = datetime.datetime.strptime(task_date_str, '%Y-%m-%d').date()
                    
                    start_dt = datetime.datetime.combine(task_date_obj, preferred_time_dt)
                    
                    est_hours = day_data.get("estimated_time_hours", daily_hours)
                    if not isinstance(est_hours, (float, int)): est_hours = daily_hours # Fallback
                    
                    end_dt = start_dt + datetime.timedelta(hours=est_hours)

                    summary = day_data.get("objective", f"{skill} - Day {day_data.get('dayNumber', '')}")
                    description = day_data.get("projects_exercises", "")
                    
                    structured_tasks_for_api.append({
                        "summary": summary,
                        "description": description,
                        "startTime": start_dt.isoformat(),
                        "endTime": end_dt.isoformat()
                    })
                    human_readable_parts.append(
                        f"Day {day_data.get('dayNumber')}: {task_date_obj.strftime('%d/%m/%Y')} - {summary}"
                    )
                except Exception as e:
                    print(f"Error processing day_data {day_data.get('dayNumber', 'N/A')}: {e}")
                    continue # Skip this task if processing fails

            human_readable_plan_str = "\n".join(human_readable_parts)
            return structured_tasks_for_api, human_readable_plan_str

        except Exception as e:
            print(f"Error generating content from AI: {e}")
            return None, str(e)

    def create_calendar_events_from_tasks(self, skill_name: str, tasks: list, local_timezone: str = 'Asia/Dhaka'):
        if not tasks:
            return "No tasks provided for calendar integration."

        # Make sure creds are valid before proceeding
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                print("Refreshing GCal token before creating events...")
                try:
                    self.creds.refresh(Request())
                    # Rebuild service if necessary, though typically not needed if creds object is updated
                    self.calendar_service = build('calendar', 'v3', credentials=self.creds)
                except Exception as e:
                    print(f"Failed to refresh GCal token: {e}")
                    return f"GCal token refresh failed: {e}"
            else:
                 return "GCal credentials are not valid. Please re-authenticate."


        created_event_links = []
        for i, task_data in enumerate(tasks):
            try:
                event_summary = f"{skill_name} - {task_data.get('summary', f'Task {i+1}')}"
                event_description = task_data.get('description', '')
                start_time_iso = task_data.get('startTime')
                end_time_iso = task_data.get('endTime')

                if not (start_time_iso and end_time_iso):
                    print(f"Skipping task due to missing start/end time: {event_summary}")
                    continue

                event = {
                    'summary': event_summary,
                    'description': event_description,
                    'start': {'dateTime': start_time_iso, 'timeZone': local_timezone},
                    'end': {'dateTime': end_time_iso, 'timeZone': local_timezone},
                }

                print(f"Creating event: {event['summary']}")
                created_event = self.calendar_service.events().insert(calendarId='primary', body=event).execute()
                created_event_links.append(created_event.get('htmlLink'))
                print(f"Event '{event['summary']}' created successfully: {created_event.get('htmlLink')}")
            except Exception as e:
                print(f"Error creating event for task '{task_data.get('summary', 'N/A')}': {e}")
        
        if created_event_links:
            return f"Successfully added {len(created_event_links)} tasks to Google Calendar.", created_event_links
        else:
            return "No events were created. Check logs for errors.", []