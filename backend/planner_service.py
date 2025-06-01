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

load_dotenv()

# --- Constants ---
GOOGLE_API_KEY_ENV_VAR = "GOOGLE_API_KEY"
GOOGLE_CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_API_VERSION = 'v3'
CALENDAR_ID_PRIMARY = 'primary'
DEFAULT_TIMEZONE = os.environ.get("DEFAULT_TIMEZONE", 'Asia/Dhaka')
GEMINI_MODEL_NAME = 'gemini-1.5-flash'

class LearningPlannerService:
    def __init__(self):
        api_key = os.environ.get(GOOGLE_API_KEY_ENV_VAR)
        if not api_key:
            # This should ideally be caught at app startup in main_api.py
            raise ValueError(f"{GOOGLE_API_KEY_ENV_VAR} not found. Service cannot start.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        self.creds = self._get_oauth_credentials()
        self.calendar_service = build('calendar', CALENDAR_API_VERSION, credentials=self.creds)

    def _get_oauth_credentials(self) -> Credentials:
        creds = None
        token_file = 'token.json'
        creds_file = 'credentials.json'

        if not os.path.exists(creds_file):
            # This check is critical. For a server, credentials.json must exist.
            # The interactive flow is problematic on a server.
            raise FileNotFoundError(
                f"{creds_file} not found. OAuth cannot proceed. "
                "Ensure it's present and an initial token.json might need to be generated manually for the server environment."
            )

        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, GOOGLE_CALENDAR_SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    print("Refreshing OAuth token for service...")
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}. Deleting old token if exists.")
                    if os.path.exists(token_file): os.remove(token_file)
                    # On a server, run_local_server is not viable.
                    # This indicates a setup issue needing manual intervention (e.g., re-auth and copy token.json)
                    # or a switch to service account credentials for non-user-specific calendar access.
                    raise ConnectionRefusedError(
                        "OAuth token refresh failed and interactive flow is not suitable for server. "
                        "Manual token refresh or alternative auth method needed."
                    ) from e # Re-raise with context
            else:
                # This part is problematic for a server. An initial token.json should exist.
                # If it needs to be created, it should be done through a separate manual process.
                print(f"Warning: No valid {token_file}. For a server, an initial token should be present. "
                      "Attempting interactive flow (may fail or block in non-interactive env)...")
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(creds_file, GOOGLE_CALENDAR_SCOPES)
                    # In a deployed environment, this run_local_server will likely fail or not be reachable.
                    # For local dev of the API, it might work if you can complete the browser flow.
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    raise ConnectionRefusedError(
                        "OAuth interactive flow failed. A pre-authorized token.json is likely needed for this environment."
                    ) from e


            with open(token_file, 'w') as token:
                token.write(creds.to_json())
            print("OAuth token obtained/refreshed and saved for service.")
        return creds

    def _extract_valid_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        if not match:
            start_index = response_text.find("{")
            end_index = response_text.rfind("}")
            if start_index != -1 and end_index != -1 and end_index > start_index:
                json_str = response_text[start_index:end_index + 1]
            else:
                return None
        else:
            json_str = match.group(1)
        try:
            json_str = re.sub(r',\s*(\}|\])', r'\1', json_str)
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None

    def _parse_preferred_time_to_datetime_time(self, preferred_time_str: Optional[str]) -> datetime.time:
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
                elif ampm_part == 'am' and hr_part == 12: hours = 0
                else: hours = hr_part
                if not (0 <= hours <= 23 and 0 <= minutes <= 59): hours, minutes = 9,0
            elif "morning" in preferred_time_str.lower(): hours = 9
            elif "afternoon" in preferred_time_str.lower(): hours = 14
            elif "evening" in preferred_time_str.lower() or "night" in preferred_time_str.lower(): hours = 19
        except Exception: pass # Default to 09:00
        return datetime.time(hours, minutes)

    def handle_chat_message(self, user_message: str, chat_history: List[Dict[str, Any]]) -> str:
        system_instruction_chat = [ # Slightly different from plan generation's specific JSON focus
            "You are a friendly and helpful AI assistant for a Skill Learning Planner app.",
            "Your primary goals are: "
            "1. Engage in natural conversation with the user about their learning interests.",
            "2. If the user expresses a desire to create a learning plan, help them clarify necessary details like the specific skill, desired duration, preferred start date, learning style (optional), preferred study time (optional), and daily study hours (optional). Ask questions one by one if needed to gather this information.",
            "3. Once sufficient details for a plan are gathered, you can summarize it and inform the user that the frontend will now call the plan generation function.",
            "4. After a plan is generated (by a separate function), you can discuss it with the user if they have questions or want to talk about refinements.",
            "5. You can also answer general questions or chat about learning.",
            f"The current date is {datetime.date.today().strftime('%Y-%m-%d')}. Use this for context if the user mentions relative dates like 'next week'."
        ]
        
        # Ensure history starts with system instruction if not already present or if history is empty
        # For API, frontend should manage full history, but this is a safeguard.
        gemini_contents = []
        if not chat_history or chat_history[0].get("role") != "system": # A conceptual system role for clarity
             gemini_contents.append({'role': 'user', 'parts': [" ".join(system_instruction_chat)]}) # System prompt as first user message
             gemini_contents.append({'role': 'model', 'parts': ["Okay, I understand my role. How can I help you today?"]})

        gemini_contents.extend(chat_history) # Add existing history passed from frontend
        gemini_contents.append({'role': 'user', 'parts': [user_message]})

        try:
            response = self.model.generate_content(contents=gemini_contents)
            return response.text.strip()
        except Exception as e:
            print(f"Error in handle_chat_message: {e}")
            return f"Sorry, I encountered an error trying to process your message: {str(e)}"

    def generate_structured_plan(self,
                                 goal: str,
                                 duration_days: int,
                                 start_date_str: str, # Expected YYYY-MM-DD
                                 learning_style: Optional[str],
                                 preferred_time_str: Optional[str], # e.g., "9 AM", "evening"
                                 daily_hours: Optional[float],
                                 chat_history_for_context: Optional[List[Dict[str, Any]]] = None,
                                 refinement_instruction: Optional[str] = None,
                                 existing_plan_tasks_for_refinement: Optional[List[Dict[str, Any]]] = None
                                 ) -> Tuple[Optional[List[Dict[str, Any]]], str]: # (structured_tasks, human_readable_or_error)

        today_date = datetime.date.today().strftime('%Y-%m-%d')
        plan_generation_system_prompt = [
            "You are an AI specialized in generating structured learning plans.",
            "When asked to generate or refine a learning plan, use the following JSON format. Ensure all details (skill, duration_days, start_date, preferred_time, daily_hours) are included at the top level of the JSON, and the learning plan steps are in the 'learningPlan' array. Wrap the JSON in ```json...``` markdown block.",
            "The 'start_date' for the overall plan and the 'date' fields within 'learningPlan' entries should be in YYYY-MM-DD format.",
            "Example Plan JSON Structure:",
            """
            ```json
            {
              "skill": "Example Skill",
              "duration_days": 3,
              "start_date": "YYYY-MM-DD", 
              "preferred_time": "morning",
              "daily_hours": 1.5,
              "learningPlan": [
                {"dayNumber": 1, "date": "YYYY-MM-DD", "objective": "Obj 1", "projects_exercises": "Ex 1", "estimated_time_hours": 1.5},
                {"dayNumber": 2, "date": "YYYY-MM-DD", "objective": "Obj 2", "projects_exercises": "Ex 2", "estimated_time_hours": 1.5},
                {"dayNumber": 3, "date": "YYYY-MM-DD", "objective": "Obj 3", "projects_exercises": "Ex 3", "estimated_time_hours": 1.5}
              ]
            }
            ```
            """,
            "If you cannot generate a plan in this format, state that you can't in plain text.",
            "Do not include any other text or comments outside the JSON block when providing a plan.",
            f"The current date is {today_date}. Use this as a reference. If the requested start_date is in the past, please adjust it to a sensible future date (e.g., next Monday or start of next available week/month)."
        ]

        gemini_contents = []
        if chat_history_for_context:
             # Assume chat_history_for_context is already in Gemini format
            gemini_contents.extend(chat_history_for_context)

        # Construct the current request based on initial generation or refinement
        current_user_prompt_parts = []
        current_user_prompt_parts.append(" ".join(plan_generation_system_prompt)) # Add system prompt as part of the user turn for this call

        if refinement_instruction and existing_plan_tasks_for_refinement:
            current_user_prompt_parts.append(f"\nRefine the existing plan for '{goal}'.")
            current_user_prompt_parts.append("Current plan tasks (JSON to be refined):")
            current_user_prompt_parts.append(json.dumps(existing_plan_tasks_for_refinement))
            current_user_prompt_parts.append(f"Refinement instruction: '{refinement_instruction}'")
            current_user_prompt_parts.append(f"The plan should still be for {duration_days} days, starting around {start_date_str} (adjust if refinement implies changes), with preferred time {preferred_time_str} and {daily_hours} daily hours.")
        else:
            current_user_prompt_parts.append(f"\nGenerate a learning plan with the following details:")
            current_user_prompt_parts.append(f"- Skill: {goal}")
            current_user_prompt_parts.append(f"- Duration: {duration_days} days")
            current_user_prompt_parts.append(f"- Start Date: {start_date_str}")
            if learning_style: current_user_prompt_parts.append(f"- Learning Style: {learning_style}")
            if preferred_time_str: current_user_prompt_parts.append(f"- Preferred Time: {preferred_time_str}")
            if daily_hours is not None: current_user_prompt_parts.append(f"- Daily Hours: {daily_hours}")
        
        gemini_contents.append({'role': 'user', 'parts': ["\n".join(current_user_prompt_parts)]})
        
        try:
            response = self.model.generate_content(contents=gemini_contents)
            ai_response_text = response.text.strip()
        except Exception as e:
            print(f"Error calling Gemini for plan generation: {e}")
            return None, f"Error communicating with AI: {str(e)}"

        parsed_json_plan = self._extract_valid_json_from_response(ai_response_text)

        if not parsed_json_plan or "learningPlan" not in parsed_json_plan:
             # Check for safety feedback if parsing failed
            try:
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    reason = response.prompt_feedback.block_reason
                    msg = response.prompt_feedback.block_reason_message
                    print(f"Plan generation blocked by API: {reason} - {msg}")
                    return None, f"Plan generation failed due to content policy: {reason}. Please rephrase. ({msg})"
            except Exception: pass
            return None, "AI did not return a valid plan in the expected JSON format. Response: " + ai_response_text[:200]


        # --- Date Correction and Structuring ---
        # Validate top-level fields from AI, use provided if AI omits
        plan_skill = parsed_json_plan.get("skill", goal)
        plan_duration = int(parsed_json_plan.get("duration_days", duration_days))
        plan_start_date_str = parsed_json_plan.get("start_date", start_date_str)
        plan_pref_time = parsed_json_plan.get("preferred_time", preferred_time_str)
        plan_daily_hours = float(parsed_json_plan.get("daily_hours", daily_hours if daily_hours is not None else 2.0))

        # Correct start date if in past
        corrected_start_datetime: datetime.datetime
        today = datetime.date.today()
        try:
            parsed_ai_start_date = datetime.datetime.strptime(plan_start_date_str, '%Y-%m-%d').date()
            if parsed_ai_start_date < today:
                # Simple correction: start next Monday
                corrected_start_datetime = datetime.datetime.combine(
                    today + datetime.timedelta(days=(7 - today.weekday())), 
                    datetime.time.min
                )
                print(f"Corrected AI start date from {plan_start_date_str} to {corrected_start_datetime.strftime('%Y-%m-%d')}")
            else:
                corrected_start_datetime = datetime.datetime.combine(parsed_ai_start_date, datetime.time.min)
        except (ValueError, TypeError):
            print(f"Invalid start_date '{plan_start_date_str}' from AI or input. Defaulting to next Monday.")
            corrected_start_datetime = datetime.datetime.combine(
                today + datetime.timedelta(days=(7 - today.weekday())), 
                datetime.time.min
            )
        
        # Update the plan JSON with corrected master start date
        parsed_json_plan["start_date"] = corrected_start_datetime.strftime('%Y-%m-%d')
        parsed_json_plan["skill"] = plan_skill
        parsed_json_plan["duration_days"] = plan_duration
        parsed_json_plan["preferred_time"] = plan_pref_time
        parsed_json_plan["daily_hours"] = plan_daily_hours
        
        # Structure into API tasks and generate human-readable plan
        structured_api_tasks = []
        human_readable_lines = [f"Learning Plan for: {plan_skill}", f"Starting: {parsed_json_plan['start_date']}\n"]
        
        preferred_dt_time_obj = self._parse_preferred_time_to_datetime_time(plan_pref_time)

        for i, day_entry in enumerate(parsed_json_plan.get("learningPlan", [])):
            day_num = day_entry.get("dayNumber", i + 1) # Ensure dayNumber
            # Correct individual task dates based on master corrected start date
            current_task_date = (corrected_start_datetime + datetime.timedelta(days=i)).date()
            day_entry["date"] = current_task_date.strftime('%Y-%m-%d')
            day_entry["dayNumber"] = day_num # Ensure dayNumber is in the entry

            objective = day_entry.get("objective", "No objective specified.")
            projects = day_entry.get("projects_exercises", "")
            task_hours = float(day_entry.get("estimated_time_hours", plan_daily_hours))

            task_start_dt = datetime.datetime.combine(current_task_date, preferred_dt_time_obj)
            task_end_dt = task_start_dt + datetime.timedelta(hours=task_hours)

            structured_api_tasks.append({
                "summary": f"Day {day_num}: {objective}",
                "description": projects,
                "startTime": task_start_dt.isoformat(),
                "endTime": task_end_dt.isoformat()
            })
            human_readable_lines.append(f"Day {day_num} ({day_entry['date']}): {objective}")
            if projects: human_readable_lines.append(f"  └ Exercises: {projects}")
        
        if not structured_api_tasks:
             return None, "Plan generated by AI but failed to structure into tasks (e.g. 'learningPlan' array was empty or items malformed)."

        # Return the modified parsed_json_plan as the human-readable part (it's the full AI output, corrected)
        # Or, for more control, the joined human_readable_lines. Let's use the detailed lines.
        return structured_api_tasks, "\n".join(human_readable_lines)


    def add_plan_to_calendar(self, skill_name: str, structured_tasks: List[Dict[str, Any]]) -> Tuple[str, Optional[List[str]]]:
        if not self.calendar_service:
            return "Calendar service not available. Please check server authentication.", None
        
        # Refresh creds just in case before a batch of writes
        try:
            if not self.creds.valid:
                self.creds.refresh(Request())
        except Exception as e:
            print(f"Could not refresh calendar token before adding events: {e}")
            # Proceed with existing creds, might fail if actually expired and unrefreshable
        
        created_event_links = []
        events_created_count = 0
        for task_data in structured_tasks:
            try:
                summary = task_data.get("summary", f"{skill_name} Task") # Ensure summary exists
                start_time_iso = task_data.get("startTime")
                end_time_iso = task_data.get("endTime")

                if not (start_time_iso and end_time_iso):
                    print(f"Skipping task '{summary}' due to missing start/end time.")
                    continue

                event_body = {
                    'summary': summary, # Already includes skill_name if formatted like "Skill - Day X: Objective"
                    'description': task_data.get('description', ''),
                    'start': {'dateTime': start_time_iso, 'timeZone': DEFAULT_TIMEZONE},
                    'end': {'dateTime': end_time_iso, 'timeZone': DEFAULT_TIMEZONE},
                }
                created_event = self.calendar_service.events().insert(calendarId=CALENDAR_ID_PRIMARY, body=event_body).execute()
                created_event_links.append(created_event.get('htmlLink'))
                events_created_count +=1
            except Exception as e:
                print(f"Error creating calendar event for task '{summary}': {e}")
        
        if events_created_count > 0:
            return f"Successfully added {events_created_count} tasks to Google Calendar.", created_event_links
        else:
            return "No events were added to Google Calendar. Check logs for details.", None