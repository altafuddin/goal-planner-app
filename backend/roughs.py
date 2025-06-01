def generate_structured_plan(
    self,
    goal: str,
    duration_days: int,
    start_date_str: str,  # Expected in YYYY-MM-DD
    learning_style: Optional[str],
    preferred_time_str: Optional[str],
    daily_hours: Optional[float],
    chat_history_for_context: Optional[List[Dict[str, Any]]] = None,
    refinement_instruction: Optional[str] = None,
    existing_plan_tasks_for_refinement: Optional[List[Dict[str, Any]]] = None
) -> Tuple[Optional[List[Dict[str, Any]]], str]:

    # --------- Enhanced Prompt ----------
    today_date = datetime.date.today().strftime('%Y-%m-%d')
    system_prompt = [
        "You are a helpful AI assistant that can generate structured learning plans.",
        "When asked to generate a learning plan, use the following JSON format. Ensure all details (skill, duration_days, start_date, preferred_time, daily_hours) are included at the top level of the JSON, and the learning plan steps are in the 'learningPlan' array. Wrap the JSON in ```json...``` markdown block.",
        "The 'start_date' for the overall plan and the 'date' fields within 'learningPlan' entries should be in YYYY-MM-DD format.",
        f"The current date is {today_date}. If the user-suggested start date is in the past, suggest something in the near future like next Monday or the first of next month.",
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
            }
          ]
        }
        ```
        """,
        "Do not include anything outside the JSON block. If you can't produce a plan, say so in plain text."
    ]

    # Combine prompt with details
    prompt_parts = [*system_prompt]
    prompt_parts.append(f"Skill: {goal}")
    prompt_parts.append(f"Duration: {duration_days} days")
    prompt_parts.append(f"Start Date: {start_date_str}")
    if learning_style: prompt_parts.append(f"Learning Style: {learning_style}")
    if preferred_time_str: prompt_parts.append(f"Preferred Time: {preferred_time_str}")
    if daily_hours: prompt_parts.append(f"Daily Study Hours: {daily_hours}")

    final_prompt = "\n".join(prompt_parts)

    # ---------- Gemini Call ----------
    try:
        response = self.model.generate_content(final_prompt)
        response_text = response.text.strip()
    except Exception as e:
        return None, f"Error calling Gemini: {str(e)}"

    # ---------- JSON Parsing ----------
    parsed_plan = self._extract_valid_json_from_response(response_text)
    if not parsed_plan or "learningPlan" not in parsed_plan:
        return None, "AI did not return a valid learning plan in expected format."

    # ---------- Field Extraction & Corrections ----------
    skill = parsed_plan.get("skill", goal)
    start_date_str = parsed_plan.get("start_date", start_date_str)
    plan_duration = int(parsed_plan.get("duration_days", duration_days))
    plan_time = parsed_plan.get("preferred_time", preferred_time_str)
    plan_hours = float(parsed_plan.get("daily_hours", daily_hours or 2.0))

    # Correct start date if in past
    today = datetime.date.today()
    try:
        ai_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if ai_date < today:
            corrected_date = datetime.date(today.year, (today.month % 12) + 1, 1)
        else:
            corrected_date = ai_date
    except Exception:
        corrected_date = datetime.date(today.year, (today.month % 12) + 1, 1)

    parsed_plan["start_date"] = corrected_date.strftime('%Y-%m-%d')

    # ---------- Recalculate Tasks ----------
    preferred_time = self._parse_preferred_time_to_datetime_time(plan_time)
    structured_tasks = []
    readable_lines = [f"📘 Learning Plan for: {skill}", f"Start Date: {parsed_plan['start_date']}\n"]

    for i, task in enumerate(parsed_plan["learningPlan"]):
        day_num = i + 1
        task_date = corrected_date + datetime.timedelta(days=i)
        task["date"] = task_date.strftime('%Y-%m-%d')
        task["dayNumber"] = day_num

        objective = task.get("objective", "No objective")
        projects = task.get("projects_exercises", "")
        est_time = float(task.get("estimated_time_hours", plan_hours))

        start_dt = datetime.datetime.combine(task_date, preferred_time)
        end_dt = start_dt + datetime.timedelta(hours=est_time)

        structured_tasks.append({
            "summary": f"Day {day_num}: {objective}",
            "description": projects,
            "startTime": start_dt.isoformat(),
            "endTime": end_dt.isoformat()
        })

        readable_lines.append(f"Day {day_num} ({task['date']}): {objective}")
        if projects:
            readable_lines.append(f"  └ Projects: {projects}")
        readable_lines.append(f"  └ Time: {est_time} hrs")

    return structured_tasks, "\n".join(readable_lines)
