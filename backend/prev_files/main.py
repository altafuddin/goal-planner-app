# main.py
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import datetime
import os

# Import your planner logic
from plan_generator import SkillLearningPlanner # Assuming SkillLearningPlannerChat was renamed

# --- Initialize your planner (globally or via dependency injection) ---
# This will attempt to load/refresh OAuth token when FastAPI starts.
# Ensure 'credentials.json' is present and 'token.json' can be created/updated.
try:
    planner = SkillLearningPlanner()
except ValueError as e: # Catch GOOGLE_API_KEY not found error
    print(f"Critical configuration error: {e}")
    # Decide how to handle - exit, or let FastAPI start but endpoints will fail
    planner = None # Or raise an exception to prevent app startup with bad config
    # For a real app, you might exit or have a placeholder service.
    exit(1) # if you want to ensure app doesn't run without proper config


app = FastAPI(
    title="Skill Learning Planner API",
    description="API to generate learning plans and integrate them with Google Calendar.",
    version="1.0.0"
)

# --- CORS (Cross-Origin Resource Sharing) ---
origins = [
    "http://localhost:3000",  # Your Next.js local dev
    # Add your Vercel frontend URL here, e.g., "https://your-app-name.vercel.app"
]
if os.environ.get("VERCEL_URL"): # Automatically add Vercel preview deployment URLs
    origins.append(f"https://{os.environ.get('VERCEL_URL')}")
if os.environ.get("NEXT_PUBLIC_VERCEL_URL"): # Or if you set it this way
     origins.append(f"https://{os.environ.get('NEXT_PUBLIC_VERCEL_URL')}")


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Schema (Request/Response Models) ---

class Task(BaseModel):
    summary: str
    description: Optional[str] = None
    startTime: str # ISO format string e.g., "2025-06-01T09:00:00"
    endTime: str   # ISO format string e.g., "2025-06-01T10:00:00"

    @validator('startTime', 'endTime')
    def check_iso_format(cls, v):
        try:
            datetime.datetime.fromisoformat(v)
        except ValueError:
            raise ValueError("Timestamp must be in ISO format")
        return v

class GeneratePlanRequest(BaseModel):
    goal: str = Field(..., example="Learn FastAPI", description="The skill to learn.")
    durationDays: int = Field(..., gt=0, example=7, description="Number of days for the plan.")
    startDate: str = Field(..., example="2025-05-30", description="Start date in YYYY-MM-DD format.")
    learningStyle: Optional[str] = Field(None, example="Visual", description="Preferred learning style (optional).")
    preferredTime: Optional[str] = Field("9 AM", example="9 AM", description="Preferred daily learning time (e.g., '9 AM', '2 PM', 'evening').")
    dailyHours: Optional[float] = Field(2.0, gt=0, example=2.5, description="Estimated daily learning hours.")

    @validator('startDate')
    def check_date_format(cls, v):
        try:
            datetime.datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError("startDate must be in YYYY-MM-DD format")
        return v

class GeneratePlanResponse(BaseModel):
    humanReadablePlan: str
    structuredTasks: List[Task]

class IntegratePlanRequest(BaseModel):
    skillName: str = Field(..., example="FastAPI Learning", description="Name of the skill for calendar event titles.")
    structuredTasks: List[Task]
    # userGoogleOauthToken: Optional[str] = None # Not needed if backend uses its own token.json

class IntegratePlanResponse(BaseModel):
    message: str
    calendarEventLinks: OptionalList[str] = None


# --- FastAPI Endpoints ---

@app.post("/generate-plan", response_model=GeneratePlanResponse, tags=["Planning"])
async def generate_plan_endpoint(request_data: GeneratePlanRequest):
    """
    Generates a learning plan based on user inputs.
    Returns a human-readable version and a list of structured tasks with calculated start/end times.
    """
    if not planner:
         raise HTTPException(status_code=503, detail="Planner service is not available due to configuration issues.")

    try:
        structured_tasks_list, human_plan = planner.generate_and_structure_plan(
            skill=request_data.goal,
            duration_days=request_data.durationDays,
            start_date_str=request_data.startDate,
            learning_style=request_data.learningStyle,
            preferred_time_str=request_data.preferredTime,
            daily_hours=request_data.dailyHours
        )

        if structured_tasks_list is None: # Indicates an error from the planner method
            raise HTTPException(status_code=500, detail=human_plan) # human_plan might contain the error message

        # Convert list of dicts to List[Task] Pydantic models for response validation
        validated_tasks = [Task(**task_data) for task_data in structured_tasks_list]

        return GeneratePlanResponse(humanReadablePlan=human_plan, structuredTasks=validated_tasks)
    except Exception as e:
        print(f"Error in /generate-plan: {e}") # Log the error
        raise HTTPException(status_code=500, detail=f"Failed to generate plan: {str(e)}")

@app.post("/integrate-plan", response_model=IntegratePlanResponse, tags=["Calendar Integration"])
async def integrate_plan_endpoint(request_data: IntegratePlanRequest):
    """
    Integrates the provided structured tasks into the user's primary Google Calendar.
    """
    if not planner:
         raise HTTPException(status_code=503, detail="Planner service is not available due to configuration issues.")
    try:
        # The planner instance already has the Google Calendar service initialized with OAuth creds
        message, links = planner.create_calendar_events_from_tasks(
            skill_name=request_data.skillName,
            tasks=[task.model_dump() for task in request_data.structuredTasks] # Convert Pydantic models to dicts
        )
        return IntegratePlanResponse(message=message, calendarEventLinks=links)
    except Exception as e:
        print(f"Error in /integrate-plan: {e}") # Log the error
        raise HTTPException(status_code=500, detail=f"Failed to integrate plan with Google Calendar: {str(e)}")

@app.get("/", tags=["General"])
async def root():
    return {"message": "Welcome to the Skill Learning Planner API!"}

# To run this (save as main.py):
# Ensure you have .env with GOOGLE_API_KEY="your_key"
# Ensure credentials.json is present.
# Run your original script once manually if token.json is not present or invalid, to perform the browser-based OAuth.
# Then run: uvicorn main:app --reload --port 8000