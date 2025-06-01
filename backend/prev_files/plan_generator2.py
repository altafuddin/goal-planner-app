# planner_logic.py
# ... (imports and other parts of the class) ...

class SkillLearningPlanner:
    def __init__(self):
        # ... (existing __init__ code for API keys, OAuth) ...
        # self.model = genai.GenerativeModel('gemini-1.5-flash') # Already there
        pass # No global chat instance here to keep the class instance itself stateless regarding chat history

    # ... (_get_oauth_credentials, _extract_valid_json, _parse_preferred_time_to_datetime remain similar) ...

    def generate_and_structure_plan(self, skill: str, duration_days: int, start_date_str: str,
                                    learning_style: str = None, preferred_time_str: str = "9 AM",
                                    daily_hours: float = 2.0,
                                    # New parameter to accept chat history for context
                                    chat_history_for_context: Optional[List[Dict[str, Any]]] = None,
                                    refinement_instruction: Optional[str] = None,
                                    existing_plan_tasks_for_refinement: Optional[List[Dict[str, Any]]] = None):
        
        # Construct the messages for Gemini
        # The `contents` list can be built from chat_history_for_context
        gemini_contents = []
        if chat_history_for_context:
            # Convert your chat history format to Gemini's expected format if necessary
            # Gemini expects a list like: [{'role': 'user', 'parts': ['Hi']}, {'role': 'model', 'parts': ['Hello!']}]
            gemini_contents.extend(chat_history_for_context)

        # Initial Prompt Construction (can be part of the chat history or a new user turn)
        prompt_parts = []
        if existing_plan_tasks_for_refinement and refinement_instruction:
            # This is a refinement scenario
            prompt_parts.append(f"I have an existing learning plan for '{skill}' and I want to refine it.")
            prompt_parts.append("Here is the current plan's structured tasks (JSON format):")
            prompt_parts.append(json.dumps(existing_plan_tasks_for_refinement, indent=2))
            prompt_parts.append(f"\nMy refinement instruction is: '{refinement_instruction}'")
            prompt_parts.append(f"\nPlease provide the complete, updated learning plan based on this refinement. The plan should still cover {duration_days} days, starting around {start_date_str} (adjust dates as necessary if the refinement implies changes to day sequence or content).")
        else:
            # This is an initial plan generation scenario
            prompt_parts.append(f"Generate a detailed {duration_days}-day learning plan for mastering {skill}.")
            start_date_obj = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            prompt_parts.append(f"The plan should include: daily learning objectives, practical projects/exercises, and estimated time commitment per day. Dates should be in ISO format (YYYY-MM-DD), starting from {start_date_obj.strftime('%Y-%m-%d')}.")
            if learning_style: prompt_parts.append(f"Consider a {learning_style} learning style.")
            if preferred_time_str: prompt_parts.append(f"Each day's activities should ideally be scheduled around {preferred_time_str}.")
            if daily_hours: prompt_parts.append(f"The total daily commitment should be around {daily_hours} hours.")

        prompt_parts.append(
            "Format the output as a structured JSON. The JSON must have a top level key named 'learningPlan' "
            "which contains a list of daily entries. Each daily entry must have 'dayNumber' (int), "
            "'date' (ISO format YYYY-MM-DD), 'objective' (string), 'projects_exercises' (string), "
            "and 'estimated_time_hours' (float or int). Do not include any comments or extra text outside the JSON. "
            "Ensure all dates in the plan strictly follow the YYYY-MM-DD format and are consistent with the start date and duration."
        )
        
        # Add the current prompt as the latest user message
        current_prompt_text = "\n".join(prompt_parts)
        gemini_contents.append({'role': 'user', 'parts': [current_prompt_text]})

        print("\nSending request to AI with context if provided...")
        try:
            response = self.model.generate_content(contents=gemini_contents) # Pass history via contents
            response_text = response.text.strip()
            # print(f"Raw AI Response: {response_text}") # For debugging
            raw_plan_json = self._extract_valid_json(response_text)

            if not raw_plan_json or "learningPlan" not in raw_plan_json:
                # Try to get error details from response if available
                try:
                    feedback = response.prompt_feedback
                    block_reason = feedback.block_reason
                    block_message = feedback.block_reason_message
                    if block_reason:
                        print(f"AI Response Blocked: {block_reason} - {block_message}")
                        return None, f"AI response was blocked: {block_reason} - {block_message}. Please rephrase or check content policies."
                except Exception:
                    pass # Ignore if feedback isn't there or fails
                return None, "Failed to parse valid plan from AI response. The response might be empty or malformed."

            # --- Structuring into Task format with start/end times (same as before) ---
            structured_tasks_for_api = []
            human_readable_parts = []
            preferred_time_dt_obj = self._parse_preferred_time_to_datetime(preferred_time_str if not refinement_instruction else "9 AM") # Use default or adapt if refinement changes preferred time

            for day_data in raw_plan_json.get("learningPlan", []):
                try:
                    task_date_str = day_data.get("date")
                    if not task_date_str: 
                        print(f"Skipping day_data due to missing date: {day_data.get('dayNumber')}")
                        continue

                    task_date_obj = datetime.datetime.strptime(task_date_str, '%Y-%m-%d').date()
                    start_dt = datetime.datetime.combine(task_date_obj, preferred_time_dt_obj)
                    
                    est_hours = day_data.get("estimated_time_hours", daily_hours)
                    if not isinstance(est_hours, (float, int)) or est_hours <= 0: est_hours = daily_hours # Fallback
                    
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
                        f"Day {day_data.get('dayNumber')}: {task_date_obj.strftime('%Y-%m-%d')} - {summary}" # Keep ISO for HR plan too for consistency
                    )
                except Exception as e:
                    print(f"Error processing day_data {day_data.get('dayNumber', 'N/A')} for structuring: {e}")
                    continue

            human_readable_plan_str = "\n".join(human_readable_parts)
            if not structured_tasks_for_api: # If all tasks failed processing
                 return None, "Plan was generated by AI, but failed to structure into tasks. Check AI response format or content."
            return structured_tasks_for_api, human_readable_plan_str

        except Exception as e:
            print(f"Error during AI content generation or processing: {e}")
            # Check if it's a GoogleGenerativeAI Error that might have more info
            if hasattr(e, 'message'):
                return None, f"AI interaction error: {e.message}"
            return None, f"An unexpected error occurred: {str(e)}"

    # ... (create_calendar_events_from_tasks remains the same) ...