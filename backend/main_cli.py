import os
import datetime
import json
import re
from typing import Dict, Any, List, Optional, Tuple

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file (for GOOGLE_API_KEY)
load_dotenv()

# --- Constants ---
GOOGLE_API_KEY_ENV_VAR = "GOOGLE_API_KEY" # Ensure your .env has this key
GOOGLE_CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_API_VERSION = 'v3'
CALENDAR_ID_PRIMARY = 'primary'
DEFAULT_TIMEZONE = os.environ.get("DEFAULT_TIMEZONE", 'Asia/Dhaka') # Allow override from env

GEMINI_MODEL_NAME = 'gemini-1.5-flash'

# Keywords for CLI interaction
INTEGRATE_COMMAND_KEYWORDS = ["integrate", "add to calendar", "sync calendar", "put on calendar", "schedule it"]
AMBIGUOUS_KEYWORDS_CLI = ["plan", "routine", "schedule", "course", "python", "javascript", "java", "c++", "web development", "data science", "ai", "machine learning", "excel"]
EXPLICIT_GENERATION_PHRASES_CLI = ["generate a plan", "create a plan", "make a plan", "learn ", "help me learn "]

class SkillLearningPlannerCLI:
    def __init__(self):
        api_key = os.environ.get(GOOGLE_API_KEY_ENV_VAR)
        if not api_key:
            print(f"FATAL ERROR: {GOOGLE_API_KEY_ENV_VAR} environment variable not set. Please set it in your .env file.")
            raise ValueError(f"{GOOGLE_API_KEY_ENV_VAR} not found.")
        genai.configure(api_key=api_key)

        self.model = genai.GenerativeModel(GEMINI_MODEL_NAME)

        self.creds = self._get_oauth_credentials()
        self.calendar_service = build('calendar', CALENDAR_API_VERSION, credentials=self.creds)
        
        today_date = datetime.date.today().strftime('%Y-%m-%d')
        enhanced_system_instruction = [
            "You are a helpful AI assistant that can generate structured learning plans and discuss them.",
            "When asked to generate a learning plan, use the following JSON format. Ensure all details (skill, duration_days, start_date, preferred_time, daily_hours) are included at the top level of the JSON, and the learning plan steps are in the 'learningPlan' array. Wrap the JSON in ```json...``` markdown block.",
            "The 'start_date' for the overall plan and the 'date' fields within 'learningPlan' entries should be in YYYY-MM-DD format.",
            "Example Plan JSON Structure:",
            """
            ```json
            {
              "skill": "Python Programming",
              "duration_days": 3,
              "start_date": "YYYY-MM-DD", 
              "preferred_time": "evening",
              "daily_hours": 2.0,
              "learningPlan": [
                {
                  "dayNumber": 1,
                  "date": "YYYY-MM-DD",
                  "objective": "Understand Python basics",
                  "projects_exercises": "Simple script",
                  "estimated_time_hours": 2.0
                },
                {
                  "dayNumber": 2,
                  "date": "YYYY-MM-DD",
                  "objective": "Data Structures",
                  "projects_exercises": "List manipulation",
                  "estimated_time_hours": 2.0
                },
                {
                  "dayNumber": 3,
                  "date": "YYYY-MM-DD",
                  "objective": "Functions and Modules",
                  "projects_exercises": "Calculator program",
                  "estimated_time_hours": 2.0
                }
              ]
            }
            ```
            """,
            "If you cannot generate a plan in this format, state that you can't.",
            "Do not include any other text or comments outside the JSON block when providing a plan.",
            f"The current date is {today_date}. Please use this as a reference for 'today', 'tomorrow', 'next week', 'next month', etc. When suggesting a start date for a plan, try to pick a date in the near future (e.g., next Monday or start of next month) if the user doesn't specify one, or if they suggest a past date."
        ]

        self.chat_session = self.model.start_chat(history=[
            {"role": "user", "parts": enhanced_system_instruction},
            {"role": "model", "parts": ["Understood. I'm ready to help you create learning plans and discuss your goals. How can I assist you today?"]}
        ])
        
        self.last_parsed_plan_data: Optional[Dict[str, Any]] = None 
        self.last_parsed_plan_details: Dict[str, Any] = {}

    def _get_oauth_credentials(self) -> Credentials:
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', GOOGLE_CALENDAR_SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}. Removing old token.json and re-authenticating...")
                    if os.path.exists('token.json'): os.remove('token.json')
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', GOOGLE_CALENDAR_SCOPES)
                    creds = flow.run_local_server(port=0)
            else:
                print("No valid token.json found or token is invalid. Attempting to authenticate...")
                if os.path.exists('credentials.json'):
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', GOOGLE_CALENDAR_SCOPES)
                    creds = flow.run_local_server(port=0)
                else:
                    print("FATAL ERROR: credentials.json not found. Please download it from Google Cloud Console and place it in the current directory.")
                    raise FileNotFoundError("credentials.json not found")
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
            print("OAuth token obtained and saved.")
        return creds

    def _extract_valid_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        # Using regex to find the JSON block specifically
        match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        if not match:
            # Fallback if markdown block not found, try to find JSON directly
            # This is less reliable and assumes AI might sometimes skip markdown
            start_index = response_text.find("{")
            end_index = response_text.rfind("}")
            if start_index != -1 and end_index != -1 and end_index > start_index:
                json_str = response_text[start_index:end_index + 1]
            else:
                return None
        else:
            json_str = match.group(1)
        
        try:
            # Basic cleaning for common AI mistakes (like trailing commas)
            json_str = re.sub(r',\s*(\}|\])', r'\1', json_str)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}. Content: {json_str[:500]}...") # Print part of problematic string
            return None

    def _parse_preferred_time_to_datetime_time(self, preferred_time_str: str) -> datetime.time:
        hours, minutes = 9, 0 # Default
        if not preferred_time_str: return datetime.time(hours, minutes)
        try:
            time_match = re.search(r'(\d{1,2})(?:[:.](\d{1,2}))?\s*(am|pm)?', preferred_time_str, re.IGNORECASE)
            if time_match:
                hr_part = int(time_match.group(1))
                min_part_str = time_match.group(2)
                minutes = int(min_part_str) if min_part_str else 0
                ampm_part = (time_match.group(3) or '').lower()

                if ampm_part == 'pm' and 1 <= hr_part < 12: hours = hr_part + 12
                elif ampm_part == 'am' and hr_part == 12: hours = 0 # 12 AM is midnight
                else: hours = hr_part # Assume 24h if no AM/PM or it's AM for 1-11
                
                if not (0 <= hours <= 23 and 0 <= minutes <= 59): hours, minutes = 9,0 # Revert to default
            elif "morning" in preferred_time_str.lower(): hours = 9
            elif "afternoon" in preferred_time_str.lower(): hours = 14
            elif "evening" in preferred_time_str.lower() or "night" in preferred_time_str.lower(): hours = 19
        except Exception as e:
            print(f"Error parsing preferred time '{preferred_time_str}': {e}. Defaulting to 09:00.")
        return datetime.time(hours, minutes)

    def _create_calendar_events_from_plan_details(self) -> str:
        if not self.calendar_service: return "Calendar service not available."
        if not self.last_parsed_plan_data or not self.last_parsed_plan_details:
            return "No plan data available to integrate."

        plan_json = self.last_parsed_plan_data
        details = self.last_parsed_plan_details

        skill = details.get("skill", "Learning Task")
        # start_date_obj should be a datetime.datetime object as stored
        start_date_obj_for_calc: datetime.datetime = details.get("start_date")
        daily_hours_float = float(details.get("daily_hours", 2.0))
        preferred_time_str = details.get("preferred_time", "9 AM")

        if not start_date_obj_for_calc: return "Start date missing in plan details."

        preferred_dt_time = self._parse_preferred_time_to_datetime_time(preferred_time_str)

        events_created_count = 0
        for day_data in plan_json.get("learningPlan", []):
            try:
                day_num = day_data.get("dayNumber")
                objective = day_data.get("objective", "Daily learning objectives")
                projects = day_data.get("projects_exercises", "")
                
                est_hours = day_data.get("estimated_time_hours")
                actual_duration_hours = float(est_hours) if isinstance(est_hours, (int, float)) and est_hours > 0 else daily_hours_float

                event_date_iso_str = day_data.get("date")
                try:
                    current_event_date = datetime.datetime.strptime(event_date_iso_str, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    print(f"Warning: Invalid or missing date for Day {day_num}, calculating from start date.")
                    # Fallback if date in task is bad, calculate from overall plan start date
                    if day_num is not None:
                         current_event_date = start_date_obj_for_calc.date() + datetime.timedelta(days=int(day_num) - 1)
                    else:
                        print(f"Skipping event for objective '{objective}' due to missing day number and invalid date.")
                        continue
                
                start_datetime_event = datetime.datetime.combine(current_event_date, preferred_dt_time)
                end_datetime_event = start_datetime_event + datetime.timedelta(hours=actual_duration_hours)

                desc_full = f"Objective: {objective}"
                if projects: desc_full += f"\nProjects/Exercises: {projects}"

                event_body = {
                    'summary': f'{skill} - Day {day_num}: {objective}',
                    'description': desc_full,
                    'start': {'dateTime': start_datetime_event.isoformat(), 'timeZone': DEFAULT_TIMEZONE},
                    'end': {'dateTime': end_datetime_event.isoformat(), 'timeZone': DEFAULT_TIMEZONE},
                }
                self.calendar_service.events().insert(calendarId=CALENDAR_ID_PRIMARY, body=event_body).execute()
                events_created_count += 1
            except Exception as e:
                print(f"Error creating calendar event for Day {day_num} ('{objective}'): {e}")
        
        return f"Successfully integrated {events_created_count} learning events." if events_created_count > 0 else "No events were integrated."

    def _format_plan_for_cli_display(self, plan_data: Dict[str, Any]) -> str:
        if not plan_data or "learningPlan" not in plan_data:
            return "Cannot display plan: Invalid structure."
        lines = [f"\n--- Learning Plan for: {plan_data.get('skill', 'N/A')} ---"]
        lines.append(f"Duration: {plan_data.get('duration_days', 'N/A')} days, Starting: {plan_data.get('start_date', 'N/A')}")
        lines.append(f"Preferred Time: {plan_data.get('preferred_time', 'N/A')}, Daily Hours: {plan_data.get('daily_hours', 'N/A')}\n")
        for day in plan_data["learningPlan"]:
            lines.append(f"Day {day.get('dayNumber')}: ({day.get('date')}) - {day.get('objective')}")
            if day.get('projects_exercises'):
                lines.append(f"  Projects/Exercises: {day.get('projects_exercises')}")
            lines.append(f"  Estimated Time: {day.get('estimated_time_hours')} hours")
        lines.append("---------------------------------------")
        return "\n".join(lines)

    def _parse_and_store_plan_cli(self, ai_response_text: str) -> bool:
        parsed_json_plan = self._extract_valid_json_from_response(ai_response_text)
        if not parsed_json_plan or "learningPlan" not in parsed_json_plan:
            # self.last_parsed_plan_data = None # Clear if new response isn't a plan
            return False

        # Basic validation of top-level fields
        skill = parsed_json_plan.get("skill")
        duration_str = str(parsed_json_plan.get("duration_days", "0")) # ensure string for isdigit
        start_date_str = parsed_json_plan.get("start_date")
        preferred_time = parsed_json_plan.get("preferred_time")
        daily_hours_str = str(parsed_json_plan.get("daily_hours", "0")) # ensure string

        if not (skill and duration_str.isdigit() and int(duration_str) > 0 and start_date_str and preferred_time and daily_hours_str):
            print("Warning: Parsed JSON plan is missing some critical top-level fields (skill, duration, start_date, preferred_time, daily_hours).")
            # self.last_parsed_plan_data = None
            return False
        
        daily_hours = float(daily_hours_str) if '.' in daily_hours_str else int(daily_hours_str)

        # Date Correction Logic
        corrected_start_date_obj: Optional[datetime.datetime] = None
        today = datetime.date.today()
        try:
            ai_suggested_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            if ai_suggested_date < today:
                print(f"Note: AI suggested start date {start_date_str} is in the past. Adjusting to a future date.")
                # Simple correction: push to same day next month, or first of next month
                target_month = today.month + (1 if ai_suggested_date.day <= today.day else 0) 
                target_year = today.year
                if target_month > 12 : 
                    target_month = 1
                    target_year += 1
                try:
                    corrected_start_date_obj = datetime.datetime(target_year, target_month, ai_suggested_date.day)
                except ValueError: # e.g. Feb 30
                    corrected_start_date_obj = datetime.datetime(target_year, target_month, 1)
                print(f"Adjusted start date to: {corrected_start_date_obj.strftime('%Y-%m-%d')}")
            else:
                corrected_start_date_obj = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
        except (ValueError, TypeError):
            print(f"Warning: Invalid start_date '{start_date_str}' in plan. Defaulting to next month.")
            corrected_start_date_obj = datetime.datetime(today.year, today.month % 12 + 1, 1)
        
        # Update plan JSON with corrected dates if necessary
        parsed_json_plan["start_date"] = corrected_start_date_obj.strftime('%Y-%m-%d')
        for i, day_entry in enumerate(parsed_json_plan.get("learningPlan", [])):
            day_entry["date"] = (corrected_start_date_obj + datetime.timedelta(days=i)).strftime('%Y-%m-%d')
            # Ensure dayNumber is consistent if missing or wrong
            day_entry["dayNumber"] = i + 1


        self.last_parsed_plan_data = parsed_json_plan
        self.last_parsed_plan_details = {
            "skill": skill,
            "duration_days": int(duration_str),
            "start_date": corrected_start_date_obj, # Store datetime object
            "preferred_time": preferred_time,
            "daily_hours": daily_hours
        }
        return True

    def _handle_cli_integration_command(self, user_input_lower: str) -> bool:
        if any(cmd in user_input_lower for cmd in INTEGRATE_COMMAND_KEYWORDS):
            if self.last_parsed_plan_data and self.last_parsed_plan_details:
                print("\nAI: Okay, attempting to add the last generated plan to your Google Calendar...")
                result_msg = self._create_calendar_events_from_plan_details()
                print(f"AI: {result_msg}")
                self.last_parsed_plan_data = None # Clear after integration attempt
                self.last_parsed_plan_details = {}
            else:
                print("\nAI: I don't have a plan ready to integrate. Please ask me to generate one first.")
            return True
        return False

    def _handle_cli_ambiguous_input(self, user_input: str, user_input_lower: str) -> bool:
        # Check only on early turns of conversation
        if len(self.chat_session.history) > 4 : # System + 1st Model + 1st User + 2nd Model
            return False

        is_ambiguous = any(kw in user_input_lower for kw in AMBIGUOUS_KEYWORDS_CLI)
        is_explicit_plan = any(phrase in user_input_lower for phrase in EXPLICIT_GENERATION_PHRASES_CLI)

        if is_ambiguous and not is_explicit_plan:
            clarification = (
                "It sounds like you're interested in a topic, perhaps for learning. "
                "To help me better, could you clarify if you'd like me to:"
                "\n1. **Generate a learning plan** (e.g., 'generate a plan for Python')?"
                "\n2. Or provide **general information** about the topic (e.g., 'tell me about Python')?"
            )
            print(f"AI: {clarification}")
            # Manually add this clarification to history for AI's context
            self.chat_session.history.append({"role": "user", "parts": [user_input]})
            self.chat_session.history.append({"role": "model", "parts": [clarification]})
            return True
        return False

    def run_cli(self):
        print("Skill Learning Planner CLI is active.")
        print("Type 'exit' to quit. If a plan is generated, type 'integrate' to add to Google Calendar.")
        while True:
            user_input = input("\nYou: ").strip()
            if user_input.lower() == 'exit':
                print("Exiting planner. Goodbye!")
                break

            user_input_lower = user_input.lower()

            if self._handle_cli_integration_command(user_input_lower):
                continue
            
            if self._handle_cli_ambiguous_input(user_input, user_input_lower):
                continue
            
            print("AI is thinking...")
            try:
                response = self.chat_session.send_message(user_input)
                ai_text_response = response.text.strip()
            except Exception as e:
                print(f"AI Error: {e}")
                continue

            if self._parse_and_store_plan_cli(ai_text_response):
                print(self._format_plan_for_cli_display(self.last_parsed_plan_data))
                print("\nAI: If this plan looks good, you can say 'integrate' to add it to your calendar, or continue chatting to refine it or ask for something else.")
            else:
                print(f"AI: {ai_text_response}")

if __name__ == "__main__":
    # --- Pre-requisite Check ---
    if not os.path.exists('credentials.json'):
        print("FATAL ERROR: 'credentials.json' not found in the current directory.")
        print("Please download your OAuth 2.0 Client ID JSON file from Google Cloud Console,")
        print("rename it to 'credentials.json', and place it in the same directory as this script.")
        exit(1)
    if not os.environ.get(GOOGLE_API_KEY_ENV_VAR):
        print(f"FATAL ERROR: The environment variable '{GOOGLE_API_KEY_ENV_VAR}' is not set.")
        print("Please create a .env file in this directory with the following content:")
        print(f"{GOOGLE_API_KEY_ENV_VAR}=your_actual_gemini_api_key")
        print("Or set the environment variable in your system.")
        exit(1)
        
    print("Starting Skill Learning Planner CLI...")
    cli_app = SkillLearningPlannerCLI()
    cli_app.run_cli()