import os
import datetime
import json
import re

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import google.generativeai as genai

class SkillLearningPlannerChat:
    def __init__(self):
        os.environ["GOOGLE_API_KEY"] = "AIzaSyB_OeDe3_rqv4JwRbFhYUnQ6-8co3R9aIs"
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
        if not os.environ.get("GOOGLE_API_KEY"):
            print("Warning: GOOGLE_API_KEY environment variable not set. Please set it or hardcode it (not recommended for production).")

        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.creds = self.get_oauth_credentials()
        self.calendar_service = build('calendar', 'v3', credentials=self.creds)
        self.chat = self.model.start_chat(history=[])
        self.current_plan = None
        self.current_skill = None
        self.current_plan_details = {}

    def get_oauth_credentials(self):
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}. Re-authenticating...")
                    if os.path.exists('token.json'):
                        os.remove('token.json')
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', self.SCOPES)
                    creds = flow.run_local_server(port=0)
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        return creds

    def extract_valid_json(self, response_text):
        try:
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            start_index = response_text.find("{")
            end_index = response_text.rfind("}")
            if start_index == -1 or end_index == -1:
                print("Warning: No JSON object found in the response.")
                return None
            
            cleaned_response = response_text[start_index:end_index + 1]
            cleaned_response = re.sub(r'//.*', '', cleaned_response)
            cleaned_response = re.sub(r',\s*}', '}', cleaned_response)
            cleaned_response = re.sub(r',\s*]', ']', cleaned_response)

            return json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            print(f"Problematic JSON string: {cleaned_response}")
            return None
        except Exception as e:
            print(f"General Error during JSON extraction: {e}")
            return None

    def generate_learning_plan(self, skill, duration_days, learning_style=None, start_date=None, preferred_time=None, daily_hours=None):
        prompt_parts = [
            f"""Generate a detailed {duration_days}-day learning plan for mastering {skill}."""
        ]
        
        prompt_parts.append(f"The plan should include: daily learning objectives, practical projects/exercises, and estimated time commitment per day. Dates should be in ISO format (YYYY-MM-DD).")

        if learning_style:
            prompt_parts.append(f"Consider a {learning_style} learning style.")
        if start_date:
            prompt_parts.append(f"The plan should start on {start_date.strftime('%Y-%m-%d')}.")
        if preferred_time:
            prompt_parts.append(f"Each day's activities should ideally be scheduled around {preferred_time}.")
        if daily_hours:
            prompt_parts.append(f"The total daily commitment should be around {daily_hours} hours.")

        prompt_parts.append("""
Format the output as a structured JSON. The JSON should have a top level key named 'learningPlan' which contains a list of daily entries. Each daily entry should have 'dayNumber', 'date' (ISO format YYYY-MM-DD), 'objective', 'projects_exercises', 'estimated_time_hours'.
Do not include any comments or extra text outside the JSON. Do not include any external resources or links.
""")
        
        prompt = "\n".join(prompt_parts)
        print("\nSending prompt to AI...")
        try:
            response = self.chat.send_message(prompt)
            response_text = response.text.strip()
            # print("Raw AI response: ", response_text) # For debugging
            return self.extract_valid_json(response_text)
        except Exception as e:
            print(f"Error generating content from AI: {e}")
            return None

    def create_calendar_events(self, skill, learning_plan, start_date_obj, daily_hours_float, preferred_time_str):
        if not learning_plan or "learningPlan" not in learning_plan or not isinstance(learning_plan["learningPlan"], list):
            print("Error: Cannot create calendar events due to invalid learning plan structure.")
            return "Invalid plan for calendar integration."

        hours, minutes = 9, 0 # Default if parsing fails
        try:
            time_match = re.search(r'(\d{1,2})(:\d{2})?\s*(am|pm)?', preferred_time_str, re.IGNORECASE)
            
            if time_match:
                hr_part = int(time_match.group(1))
                min_part = time_match.group(2)
                ampm_part = (time_match.group(3) or '').lower()

                minutes = int(min_part[1:]) if min_part else 0

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
            else:
                print(f"Warning: Could not parse preferred time '{preferred_time_str}'. Defaulting to 09:00.")

        except (ValueError, TypeError, AttributeError) as e:
            print(f"Error parsing preferred time '{preferred_time_str}': {e}. Defaulting to 09:00.")
            hours, minutes = 9, 0


        local_timezone = 'Asia/Dhaka'

        for day_data in learning_plan["learningPlan"]:
            try:
                day_num = day_data.get("dayNumber")
                objective = day_data.get("objective", "Daily learning objectives")
                projects_exercises = day_data.get("projects_exercises", "")
                
                estimated_time_from_plan = day_data.get("estimated_time_hours")
                if isinstance(estimated_time_from_plan, (int, float)):
                    actual_event_duration = estimated_time_from_plan
                else:
                    actual_event_duration = daily_hours_float

                event_date_str = day_data.get("date")
                if event_date_str:
                    current_event_date = datetime.datetime.strptime(event_date_str, '%Y-%m-%d').date()
                else:
                    current_event_date = start_date_obj.date() + datetime.timedelta(days=day_num - 1)
                
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
                        'timeZone': local_timezone,
                    },
                    'end': {
                        'dateTime': end_datetime.isoformat(),
                        'timeZone': local_timezone,
                        "endTimeUnspecified": False,
                    },
                }

                print(f"Creating event for Day {day_num}: {event['summary']}")
                self.calendar_service.events().insert(calendarId='primary', body=event).execute()
                print(f"Event for Day {day_num} created successfully.")
            except Exception as e:
                print(f"Error creating event for Day {day_num}: {e}")
        return "All available events integrated into Google Calendar."

    def chat_with_ai(self, user_input):
        try:
            response = self.chat.send_message(user_input)
            return response.text.strip()
        except Exception as e:
            print(f"Error getting AI chat response: {e}")
            return "I'm sorry, I'm having trouble connecting right now."

    def _format_plan_for_display(self, learning_plan):
        """
        Formats the learning plan for user-friendly console display.
        """
        if not learning_plan or "learningPlan" not in learning_plan or not isinstance(learning_plan["learningPlan"], list):
            return "Unable to display plan: Invalid format."

        formatted_output = []
        for day_data in learning_plan["learningPlan"]:
            day_num = day_data.get("dayNumber")
            date_str = day_data.get("date")
            objective = day_data.get("objective", "No objective specified.")
            
            display_date = date_str # Default to ISO if parsing fails
            if date_str:
                try:
                    # Convert YYYY-MM-DD to DD/MM/YYYY for display
                    parsed_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                    display_date = parsed_date.strftime('%d/%m/%Y')
                except ValueError:
                    pass # Keep original if parsing fails

            formatted_output.append(f"Day {day_num}: {display_date} - {objective}")
            # Optionally add more details if you want:
            # projects = day_data.get("projects_exercises")
            # if projects:
            #     formatted_output.append(f"  Projects: {projects}")
            # time_estimate = day_data.get("estimated_time_hours")
            # if time_estimate:
            #     formatted_output.append(f"  Time: {time_estimate} hours")
            # formatted_output.append("-" * 30) # Separator for readability

        return "\n".join(formatted_output)

    def run(self):
        print("Welcome to your Skill Learning Planner! Ask me anything, or tell me to 'plan' a skill.")
        while True:
            user_input = input("\nYou: ").strip()

            if user_input.lower() == 'exit':
                print("Goodbye!")
                break
            
            plan_keywords = ["plan", "create plan", "generate plan", "make a plan", "schedule a plan"]
            if any(phrase in user_input.lower() for phrase in plan_keywords):
                print("\nOkay, let's create a learning plan!")
                self.current_skill = input("What skill do you want to learn? ")
                
                while True:
                    try:
                        duration_str = input("How many days do you want to dedicate to learning? (e.g., 8) ")
                        duration = int(duration_str)
                        if duration <= 0:
                            print("Duration must be a positive number.")
                            continue
                        break
                    except ValueError:
                        print("Please enter a valid number for days.")

                learning_style = input("Do you have a specific learning style? (e.g., Visual, Auditory, Kinesthetic, Read/Write, Optional) ")
                
                while True:
                    start_date_str = input("When do you want to start? (DD/MM/YYYY, e.g., 27/05/2025) ")
                    try:
                        start_date_obj = datetime.datetime.strptime(start_date_str, '%d/%m/%Y')
                        break
                    except ValueError:
                        print("Invalid date format. Please use DD/MM/YYYY.")
                
                preferred_time = input("What time of day do you prefer to learn? (e.g., 9 AM, 2 PM, evening) ")
                
                while True:
                    daily_hours_str = input("How many hours daily do you want to dedicate? (e.g., 2, 0.5) ")
                    try:
                        daily_hours_float = float(daily_hours_str)
                        if daily_hours_float <= 0:
                            print("Daily hours must be a positive number.")
                            continue
                        break
                    except ValueError:
                        print("Please enter a valid number for hours.")

                self.current_plan_details = {
                    "skill": self.current_skill,
                    "start_date": start_date_obj,
                    "preferred_time": preferred_time,
                    "daily_hours": daily_hours_float
                }

                plan_generated_successfully = False
                while True:
                    self.current_plan = self.generate_learning_plan(
                        self.current_skill,
                        duration,
                        learning_style,
                        start_date=start_date_obj,
                        preferred_time=preferred_time,
                        daily_hours=daily_hours_float
                    )

                    if self.current_plan:
                        print("\n--- Generated Learning Plan ---")
                        # Display the formatted plan here
                        print(self._format_plan_for_display(self.current_plan))
                        print("-------------------------------")
                        plan_generated_successfully = True
                    else:
                        print("Failed to generate a valid learning plan. Let's try again with the same details.")
                        plan_generated_successfully = False

                    action_prompt = "\nWhat would you like to do with this plan? You can say 'integrate', 'generate new', or 'go back to chat'."
                    action_input = input(action_prompt).lower().strip()

                    integrate_keywords = ["integrate", "yes", "ok", "please integrate", "do it", "add to calendar"]
                    new_plan_keywords = ["new", "generate new", "another one", "regenerate", "different plan"]
                    
                    if any(phrase in action_input for phrase in integrate_keywords):
                        if plan_generated_successfully:
                            print("\nIntegrating plan to Google Calendar...")
                            result = self.create_calendar_events(
                                self.current_plan_details["skill"],
                                self.current_plan,
                                self.current_plan_details["start_date"],
                                self.current_plan_details["daily_hours"],
                                self.current_plan_details["preferred_time"]
                            )
                            print(f"\nIntegration result: {result}")
                            self.current_plan = None
                            self.current_skill = None
                            self.current_plan_details = {}
                            break
                        else:
                            print("No valid plan to integrate. Please generate one first.")
                            continue
                    elif any(phrase in action_input for phrase in new_plan_keywords):
                        print("Okay, generating a new plan with the same details...")
                        # Loop continues to generate a new plan
                    else:
                        print("Okay, returning to general chat. Your generated plan is dismissed.")
                        self.current_plan = None
                        self.current_skill = None
                        self.current_plan_details = {}
                        break
            
            else:
                ai_response = self.chat_with_ai(user_input)
                print(f"AI: {ai_response}")

if __name__ == "__main__":
    planner_chat = SkillLearningPlannerChat()
    planner_chat.run()