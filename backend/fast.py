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

# --- Constants (from previous code, keep them) ---
GOOGLE_API_KEY_ENV_VAR = "GOOGLE_API_KEY"
GOOGLE_CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_API_VERSION = 'v3'
CALENDAR_ID_PRIMARY = 'primary'
DEFAULT_TIMEZONE = 'Asia/Dhaka' 

GEMINI_MODEL_NAME = 'gemini-1.5-flash'

INTEGRATE_COMMAND_KEYWORDS = ["integrate", "add to calendar", "sync calendar", "put on calendar", "schedule it"]
AMBIGUOUS_KEYWORDS = ["plan", "routine", "schedule", "course", "python", "javascript", "java", "c++", "web development", "data science", "ai", "machine learning", "excel"]
EXPLICIT_GENERATION_PHRASES = ["generate a plan", "create a plan", "make a plan", "learn ", "help me learn "]

# --- Conceptual Tool Definitions for Gemini (This is how the model 'sees' the tool) ---
# In a real setup, this would be part of your genai.GenerativeModel initialization
# For demonstration purposes, I'm showing how this tool would be structured conceptually
# The actual `Calendar` module with its functions would be imported and callable.
calendar_tool_definition = {
    "name": "create_calendar_event",
    "description": "Creates a new event in the user's Google Calendar.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "The title or summary of the event."},
            "start_date": {"type": "string", "description": "The start date of the event in YYYY-MM-DD format."},
            "start_time_of_day": {"type": "string", "description": "The start time of the event in HH:MM:SS format (24-hour)."},
            "start_am_pm_or_unknown": {"type": "string", "description": "AM/PM designation for the start time, if provided. e.g., 'PM'"},
            "end_date": {"type": "string", "description": "The end date of the event in YYYY-MM-DD format (optional)."},
            "end_time_of_day": {"type": "string", "description": "The end time of the event in HH:MM:SS format (24-hour, optional)."},
            "end_am_pm_or_unknown": {"type": "string", "description": "AM/PM designation for the end time, if provided. e.g., 'PM' (optional)."},
            "description": {"type": "string", "description": "A detailed description of the event (optional)."},
            "location_name": {"type": "string", "description": "The location of the event (optional)."},
            "attendees": {"type": "array", "items": {"type": "string"}, "description": "A list of email addresses of attendees (optional)."}
        },
        "required": ["title", "start_date", "start_time_of_day", "start_am_pm_or_unknown"]
    }
}

# Assume 'generic_calendar' is an imported module with the actual function that handles API calls
# This part of the code would directly invoke that function.
# For this demonstration, I'm just showing the core class structure.
# You would need to ensure `Calendar` is available and correctly integrated as a tool.

class SkillLearningPlannerChat:
    def __init__(self):
        # Configure Generative AI
        api_key = os.environ.get(GOOGLE_API_KEY_ENV_VAR)
        if not api_key:
            print(f"Warning: {GOOGLE_API_KEY_ENV_VAR} environment variable not set. Please set it or hardcode it (not recommended for production).")
        genai.configure(api_key=api_key)

        # Initialize the model with the tool definitions
        # In a real application, tools would be passed here:
        # self.model = genai.GenerativeModel(GEMINI_MODEL_NAME, tools=[your_calendar_tool_object])
        self.model = genai.GenerativeModel(GEMINI_MODEL_NAME) # No tools explicitly defined here for this snippet

        # Google Calendar API Setup
        self.creds = self._get_oauth_credentials()
        self.calendar_service = build('calendar', CALENDAR_API_VERSION, credentials=self.creds)
        
        # Initialize chat history with system instructions
        today_date = datetime.date.today().strftime('%Y-%m-%d')

        # --- KEY IMPROVEMENT: Enhanced System Prompt for Tool Use ---
        enhanced_system_instruction = [
            "You are a helpful AI assistant that can generate structured learning plans and **manage calendar events**.",
            "You have access to a tool for creating calendar events. When the user asks to **create, schedule, add, or put an event/meeting on their calendar**, you MUST use the `Calendar` function.",
            "When using `Calendar`, you need to extract the event **title**, **start date**, and **start time**. If an end time or description is provided, include those too.",
            "**Example of how to use the tool internally (do not show this to user):**",
            "`print(create_calendar_event(title='Meeting with John', start_date='2025-06-15', start_time_of_day='14:00:00', start_am_pm_or_unknown='PM', description='Discuss project progress'))`",
            "If the user asks for a date or time that is ambiguous (e.g., 'tomorrow', 'next week'), resolve it based on the current date.",
            "If the user asks to create an event but *doesn't provide a specific date or time*, politely ask for it.",
            "---",
            "For **learning plan generation**, use the following JSON format. Ensure all details (skill, duration in days, start date, preferred time, daily hours) are included at the top level of the JSON, and the learning plan steps are in the 'learningPlan' array. Wrap the JSON in ```json...``` markdown block.",
            "The 'start_date' and 'date' fields within 'learningPlan' should be inYYYY-MM-DD format.",
            "Example Plan JSON Structure:",
            """
            ```json
            {
              "skill": "Python Programming",
              "duration_days": 30,
              "start_date": "YYYY-MM-DD",
              "preferred_time": "evening",
              "daily_hours": 2.5,
              "learningPlan": [
                {
                  "dayNumber": 1,
                  "date": "YYYY-MM-DD",
                  "objective": "Understand Python basics (variables, data types)",
                  "projects_exercises": "Write a script to calculate area of a circle",
                  "estimated_time_hours": 2.5
                }
              ]
            }
            ```
            """,
            "If you cannot generate a plan in this format, state that you can't.",
            "Do not include any other text or comments outside the JSON block when providing a plan.",
            f"The current date is {today_date}. Please use this as a reference for 'today', 'tomorrow', 'next week', 'next month', etc."
        ]


        self.chat = self.model.start_chat(history=[
            {
                "role": "user",
                "parts": enhanced_system_instruction # Use the enhanced instructions
            },
            {
                "role": "model",
                "parts": ["Understood. How can I help you today?"]
            }
        ])
        
        self.last_parsed_plan_data: Optional[Dict[str, Any]] = None 
        self.last_parsed_plan_details: Dict[str, Any] = {} 

    # --- (All other methods like _get_oauth_credentials, extract_valid_json, etc., remain the same) ---
    # I'll just provide the relevant ones that might be called by the model or have minor changes.

    def _get_oauth_credentials(self) -> Credentials:
        """Retrieves or refreshes Google OAuth credentials."""
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', GOOGLE_CALENDAR_SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}. Re-authenticating...")
                    if os.path.exists('token.json'):
                        os.remove('token.json') # Remove old token to force re-auth
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', GOOGLE_CALENDAR_SCOPES)
                    creds = flow.run_local_server(port=0)
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', GOOGLE_CALENDAR_SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        return creds

    def extract_valid_json(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Extracts a valid JSON object from a given string, handling markdown and comments.
        """
        try:
            # Remove markdown code block fences
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            # Find the actual JSON object
            start_index = response_text.find("{")
            end_index = response_text.rfind("}")
            if start_index == -1 or end_index == -1:
                return None # No JSON object found
            
            cleaned_response = response_text[start_index:end_index + 1]
            
            # Remove single-line comments (often generated by AI)
            cleaned_response = re.sub(r'//.*', '', cleaned_response) 
            # Remove trailing commas before closing braces/brackets (invalid JSON)
            cleaned_response = re.sub(r',\s*}', '}', cleaned_response) 
            cleaned_response = re.sub(r',\s*]', ']', cleaned_response) 

            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            return None
        except Exception:
            return None

    def create_calendar_events(self, skill: str, learning_plan_data: Dict[str, Any], 
                               start_date_obj: datetime.datetime, daily_hours_float: float, 
                               preferred_time_str: str) -> str:
        """
        Creates Google Calendar events based on the parsed learning plan data.
        """
        if not self.calendar_service:
            return "Calendar service not available. Please authenticate to Google Calendar first."

        if not learning_plan_data.get("learningPlan") or not isinstance(learning_plan_data["learningPlan"], list):
            return "Invalid plan for calendar integration."

        hours, minutes = 9, 0 # Default if preferred_time_str parsing fails
        try:
            time_match = re.search(r'(\d{1,2})(:\d{2})?\s*(am|pm)?', preferred_time_str, re.IGNORECASE)
            
            if time_match:
                hr_part = int(time_match.group(1))
                min_part = int(time_match.group(2)[1:]) if time_match.group(2) else 0
                ampm_part = (time_match.group(3) or '').lower()

                if ampm_part == 'pm' and hr_part < 12:
                    hours = hr_part + 12
                elif ampm_part == 'am' and hr_part == 12: # 12 AM (midnight)
                    hours = 0
                elif not ampm_part and hr_part > 12: # Assume 24-hour if no AM/PM and > 12
                    hours = hr_part
                else:
                    hours = hr_part
            elif "morning" in preferred_time_str.lower():
                hours = 9
            elif "afternoon" in preferred_time_str.lower():
                hours = 14
            elif "evening" in preferred_time_str.lower() or "night" in preferred_time_str.lower():
                hours = 19

        except (ValueError, TypeError, AttributeError):
            pass # Use default 09:00

        events_created_count = 0
        for day_data in learning_plan_data["learningPlan"]:
            try:
                day_num = day_data.get("dayNumber")
                objective = day_data.get("objective", "Daily learning objectives")
                projects_exercises = day_data.get("projects_exercises", "")
                
                estimated_time_from_plan = day_data.get("estimated_time_hours")
                actual_event_duration = estimated_time_from_plan if isinstance(estimated_time_from_plan, (int, float)) else daily_hours_float

                event_date_str = day_data.get("date")
                current_event_date: Optional[datetime.date] = None
                if event_date_str:
                    try:
                        current_event_date = datetime.datetime.strptime(event_date_str, '%Y-%m-%d').date()
                    except ValueError:
                        pass # current_event_date remains None, fallback logic will handle

                if not current_event_date and day_num is not None:
                    # Fallback: if date is missing or invalid in specific entry, calculate from overall start date
                    current_event_date = start_date_obj.date() + datetime.timedelta(days=day_num - 1)
                
                if not current_event_date:
                    continue # Cannot determine a valid date for this event, skip it

                start_datetime = datetime.datetime.combine(current_event_date, datetime.time(hours, minutes))
                end_datetime = start_datetime + datetime.timedelta(hours=actual_event_duration)

                description_full = f"Objective: {objective}"
                if projects_exercises:
                    description_full += f"\nProjects/Exercises: {projects_exercises}"

                event = {
                    'summary': f'{skill} Learning - Day {day_num}',
                    'description': description_full,
                    'start': {
                        'dateTime': start_datetime.isoformat(),
                        'timeZone': DEFAULT_TIMEZONE,
                    },
                    'end': {
                        'dateTime': end_datetime.isoformat(),
                        'timeZone': DEFAULT_TIMEZONE,
                        "endTimeUnspecified": False,
                    },
                }

                print(f"Creating event for Day {day_num}: {event['summary']}")
                self.calendar_service.events().insert(calendarId=CALENDAR_ID_PRIMARY, body=event).execute()
                print(f"Event for Day {day_num} created successfully.")
                events_created_count += 1
            except Exception as e:
                print(f"Error creating event for Day {day_num}: {e}")
        
        if events_created_count > 0:
            return f"Successfully integrated {events_created_count} learning events into Google Calendar."
        else:
            return "No events could be integrated into Google Calendar. Please check the plan details and calendar access."

    def _format_plan_for_display(self, plan_data: Dict[str, Any]) -> str:
        """
        Formats the structured learning plan data into a human-readable string.
        """
        if not plan_data or "learningPlan" not in plan_data or not isinstance(plan_data["learningPlan"], list):
            return "Unable to display plan in a human-readable format due to incorrect structure."

        formatted_lines: List[str] = []
        skill = plan_data.get("skill", "Learning")
        start_date_display = plan_data.get("start_date", "N/A")
        
        formatted_lines.append(f"\n--- Your Learning Plan for **{skill}** (Starting **{start_date_display}**) ---")
        
        for day_entry in plan_data["learningPlan"]:
            date_str = day_entry.get("date", "N/A")
            objective = day_entry.get("objective", "No objective specified.")
            projects_exercises = day_entry.get("projects_exercises", "")
            
            try:
                display_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').strftime('%b %d, %Y')
            except ValueError:
                display_date = date_str # Fallback if parsing fails

            line = f"- **{display_date}**: {objective}"
            if projects_exercises:
                line += f" (Exercises: {projects_exercises})"
            formatted_lines.append(line)
        
        formatted_lines.append("--------------------------------------------------")
        return "\n".join(formatted_lines)

    def _parse_and_store_plan_from_ai_response(self, ai_response_text: str) -> bool:
        """
        Attempts to extract a learning plan JSON from the AI's response.
        If a valid plan is found, it stores it and its details,
        applying intelligent date corrections.
        Returns True if a plan was successfully stored, False otherwise.
        """
        parsed_data = self.extract_valid_json(ai_response_text)
        
        if not parsed_data or "learningPlan" not in parsed_data or not isinstance(parsed_data["learningPlan"], list):
            return False

        # Extract main plan details from the top level of the JSON
        skill = parsed_data.get("skill")
        duration_days = parsed_data.get("duration_days")
        start_date_str = parsed_data.get("start_date")
        preferred_time = parsed_data.get("preferred_time")
        daily_hours = parsed_data.get("daily_hours")

        start_date_obj: Optional[datetime.datetime] = None
        corrected_to_future_date = False 
        today = datetime.date.today()

        try:
            ai_suggested_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            
            # If AI suggested a past date, correct it
            if ai_suggested_date < today:
                target_month = today.month + 1
                target_year = today.year
                if target_month > 12:
                    target_month = 1
                    target_year += 1
                
                target_day = ai_suggested_date.day # Preserve AI's day if possible
                try:
                    potential_corrected_date = datetime.date(target_year, target_month, target_day)
                    start_date_obj = datetime.datetime.combine(potential_corrected_date, datetime.time())
                except ValueError: # If AI's day is invalid for target month (e.g., Feb 30th)
                    start_date_obj = datetime.datetime.combine(datetime.date(target_year, target_month, 1), datetime.time())

                corrected_to_future_date = True
            else:
                # If AI's date is in the future or today, use it directly
                start_date_obj = datetime.datetime.combine(ai_suggested_date, datetime.time())

        except (ValueError, TypeError): # If start_date_str is unparseable
            target_month = today.month + 1
            target_year = today.year
            if target_month > 12:
                target_month = 1
                target_year += 1
            start_date_obj = datetime.datetime.combine(datetime.date(target_year, target_month, 1), datetime.time())
            corrected_to_future_date = True
        
        if not start_date_obj:
            return False

        # Validate other crucial fields for integration after date correction
        if not all([skill, preferred_time, daily_hours is not None]):
            return False 

        # If a correction occurred, update all dates in the learningPlan array based on the new start_date_obj
        if corrected_to_future_date:
            for day_entry in parsed_data["learningPlan"]:
                day_num = day_entry.get("dayNumber", 1) # Default to 1 if dayNumber is missing
                corrected_day_date = start_date_obj.date() + datetime.timedelta(days=day_num - 1)
                day_entry["date"] = corrected_day_date.strftime('%Y-%m-%d')
            parsed_data["start_date"] = start_date_obj.date().strftime('%Y-%m-%d') # Update top-level start_date in parsed_data

        self.last_parsed_plan_data = parsed_data # Store the (possibly modified) full JSON plan
        self.last_parsed_plan_details = {
            "skill": skill,
            "duration_days": duration_days,
            "start_date": start_date_obj, # This is the corrected datetime object
            "preferred_time": preferred_time,
            "daily_hours": float(daily_hours) # Ensure float for calculations
        }
        return True # Indicate that a plan was successfully stored

    def chat_with_ai(self, user_input: str) -> str:
        """Sends user input to the AI and returns the AI's response."""
        try:
            response = self.chat.send_message(user_input)
            ai_response_text = response.text.strip()
            return ai_response_text
        except Exception as e:
            return f"I'm sorry, I'm having trouble connecting right now: {e}"

    def _handle_integration_command(self, user_input: str) -> bool:
        """
        Handles user commands related to calendar integration.
        Returns True if an integration command was processed, False otherwise.
        """
        if any(phrase in user_input.lower() for phrase in INTEGRATE_COMMAND_KEYWORDS):
            if self.last_parsed_plan_data and self.last_parsed_plan_details:
                print("Attempting to integrate the last generated plan...")
                integration_message = self.create_calendar_events(
                    self.last_parsed_plan_details["skill"],
                    self.last_parsed_plan_data,
                    self.last_parsed_plan_details["start_date"],
                    self.last_parsed_plan_details["daily_hours"],
                    self.last_parsed_plan_details["preferred_time"]
                )
                print(f"\nAI: {integration_message}")
                self.last_parsed_plan_data = None # Clear stored plan after attempt
                self.last_parsed_plan_details = {}
            else:
                print("\nAI: I don't have a recent learning plan to integrate. Please ask me to generate one first.")
            return True
        return False

    def _handle_ambiguous_initial_input(self, user_input: str) -> bool:
        """
        Checks for ambiguous initial user inputs and provides clarification.
        Returns True if clarification was issued, False otherwise.
        """
        # len(self.chat.history) <= 2 means only initial system setup messages are in history.
        is_early_turn = len(self.chat.history) <= 2 
        user_input_lower = user_input.lower()

        # Check for whole words in ambiguous keywords
        is_ambiguous_keyword_present = any(kw in user_input_lower.split() for kw in AMBIGUOUS_KEYWORDS)
        
        # Check if the input explicitly asks for a plan generation
        is_explicit_generation_request = any(phrase in user_input_lower for phrase in EXPLICIT_GENERATION_PHRASES)

        if is_early_turn and is_ambiguous_keyword_present and not is_explicit_generation_request:
            clarification_response = (
                "A term like 'plan' or a skill name can be very broad! "
                "Are you trying to **generate a learning plan** for this, "
                "or are you looking for **general information** about it?"
                "\n\nFor example, you could say: "
                "'Generate a Python learning plan' or 'Tell me about Python'."
            )
            print(f"AI: {clarification_response}")
            
            # Manually add this interaction to history so the AI has context for the next turn
            self.chat.history.append({"role": "user", "parts": [user_input]})
            self.chat.history.append({"role": "model", "parts": [clarification_response]})
            return True
        return False

    def run(self):
        """Main loop for the conversational AI."""
        print("Welcome to your Skill Learning Planner! Just chat with me naturally. If you want a learning plan, ask for it!")
        print("Once I provide a plan, you can say 'integrate' to add it to your Google Calendar.")
        
        while True:
            user_input = input("\nYou: ").strip()

            if user_input.lower() == 'exit':
                print("Goodbye!")
                break
            
            # Priority 1: Handle calendar integration commands
            if self._handle_integration_command(user_input):
                continue
            
            # Priority 2: Handle ambiguous initial inputs
            if self._handle_ambiguous_initial_input(user_input):
                continue
            
            # Priority 3: Send to AI for general chat or plan generation
            ai_response = self.chat_with_ai(user_input)
            
            # Always attempt to parse the AI's response for a plan, even if it's not the primary intent
            plan_found_and_stored = self._parse_and_store_plan_from_ai_response(ai_response)

            if plan_found_and_stored:
                # If a plan was found, format and display it nicely to the user
                formatted_plan_output = self._format_plan_for_display(self.last_parsed_plan_data)
                print(f"AI: {formatted_plan_output}")
                print("\nAI: If this looks good, say '**integrate**' to add it to your calendar!")
            else:
                # If no plan was found, display the AI's raw chat response directly
                print(f"AI: {ai_response}")


if __name__ == "__main__":
    planner_chat = SkillLearningPlannerChat()
    planner_chat.run()