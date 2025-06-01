from typing import List, Dict, Any


class PlanGenerator:
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