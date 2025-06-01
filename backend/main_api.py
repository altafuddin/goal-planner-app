# main_api.py
import os
import datetime
from fastapi import FastAPI, HTTPException, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Any

# Import your planner logic class
try:
    from planner_service import LearningPlannerService
except ImportError:
    print("ERROR: planner_service.py not found or LearningPlannerService class not defined.")
    # Fallback for environments where service might not be fully ready (e.g. initial setup)
    LearningPlannerService = None 

# --- Environment Variable Checks ---
# These should ideally be checked before Uvicorn even starts the app,
# but an early check here can prevent the app from running with fatal misconfigurations.
if not os.path.exists('credentials.json'):
    print("FATAL API STARTUP ERROR: 'credentials.json' not found.")
    print("The API cannot function without Google OAuth credentials.")
    # In a real deployment, you might have a script that prevents startup,
    # or the app will fail when LearningPlannerService tries to init.
    # For now, we'll let it potentially fail at planner instantiation.

if not os.environ.get("GOOGLE_API_KEY"):
    print("FATAL API STARTUP ERROR: 'GOOGLE_API_KEY' environment variable not set.")
    print("The API cannot function without a Gemini API Key.")


# --- Initialize Planner Service ---
planner_service_instance = None   # type: Optional[LearningPlannerService]
try:
    if LearningPlannerService: # Check if class was imported
        planner_service_instance = LearningPlannerService()
    else: # If import failed
        raise RuntimeError("LearningPlannerService class could not be imported. API cannot start.")
except FileNotFoundError as e: # Specifically catch credentials.json missing during init
    print(f"FATAL API STARTUP ERROR during planner service initialization: {e}")
    planner_service_instance = None # Ensure it's None so endpoints can check
except ValueError as e: # Catch API key missing during init
    print(f"FATAL API STARTUP ERROR during planner service initialization: {e}")
    planner_service_instance = None
except Exception as e: # Catch other init errors like OAuth interactive failures
    print(f"UNEXPECTED API STARTUP ERROR during planner service initialization: {e}")
    print("This might be due to OAuth issues requiring manual intervention (e.g., generating token.json).")
    planner_service_instance = None


app = FastAPI(
    title="Learning Plan Generator API",
    description="API for conversational learning plan generation and Google Calendar integration.",
    version="1.1.0",
    # If planner_service_instance is None, the API docs might still load,
    # but endpoints will return 503. This is often preferred over outright crashing the HTTP server.
    # You could also raise an exception here to prevent FastAPI from starting if config is bad.
)

# --- CORS Configuration ---
origins = [
    "http://localhost:3000",  # Next.js local dev
    # Add your deployed frontend Vercel URL(s) here (production and previews)
    # e.g., "https://your-app-name.vercel.app",
    # If backend is also on Vercel, Vercel sets ORIGIN env var.
    # If using other platforms, explicitly list frontend origins.
]
# Example for Vercel deployment if frontend sets NEXT_PUBLIC_VERCEL_URL
vercel_url = os.environ.get("NEXT_PUBLIC_VERCEL_URL")
if vercel_url and not vercel_url.startswith("localhost"): # Avoid adding localhost again if it's set
    origins.append(f"https://{vercel_url}")


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)

# --- Pydantic Models for API Requests and Responses ---

# For Gemini Content structure (role and parts)
class GeminiContentPart(BaseModel):
    text: str
    # inline_data: Optional[Dict] = None # For multimodal, not used yet

class GeminiContent(BaseModel):
    role: str # "user" or "model"
    parts: List[GeminiContentPart] # Using our part model

    # Pydantic v2 config
    model_config = ConfigDict(protected_namespaces=())


class ChatMessageRequest(BaseModel):
    userMessage: str = Field(..., description="The user's current message.")
    chatHistory: List[GeminiContent] = Field(default_factory=list, description="The conversation history.")

class ChatMessageResponse(BaseModel):
    aiResponse: str

class Task(BaseModel):
    summary: str
    description: Optional[str] = None
    startTime: str # ISO format string
    endTime: str   # ISO format string

    @field_validator('startTime', 'endTime')
    @classmethod
    def check_iso_format(cls, v: str) -> str:
        try:
            # Handle 'Z' for UTC explicitly if fromisoformat doesn't like it directly sometimes
            dt_obj = datetime.datetime.fromisoformat(v.replace('Z', '+00:00'))
            # For this app, let's assume we don't need to enforce timezone awareness here,
            # as Google Calendar API handles timezones well.
            # But it's good that it's an ISO string.
        except ValueError:
            raise ValueError(f"Timestamp '{v}' must be in ISO format.")
        return v

class GeneratePlanRequest(BaseModel):
    goal: str = Field(..., example="Learn Advanced Python")
    durationDays: int = Field(..., gt=0, example=10)
    startDate: str = Field(..., example=datetime.date.today().strftime('%Y-%m-%d')) # Default to today for example
    
    learningStyle: Optional[str] = Field(None, example="Project-based")
    preferredTime: Optional[str] = Field("Anytime", example="Morning", description="e.g., Morning, 2 PM, Evening, Anytime")
    dailyHours: Optional[float] = Field(2.0, gt=0, example=3.0)
    
    chatHistoryForContext: Optional[List[GeminiContent]] = Field(default_factory=list)
    refinementInstruction: Optional[str] = Field(None)
    existingPlanTasksForRefinement: Optional[List[Task]] = Field(default_factory=list)

    @field_validator('startDate')
    @classmethod
    def check_date_format(cls, v: str) -> str:
        try:
            datetime.datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError("startDate must be in YYYY-MM-DD format.")
        return v

class GeneratePlanResponse(BaseModel):
    humanReadablePlan: str # Could be the full JSON plan string or a formatted summary
    structuredTasks: List[Task]

class IntegratePlanRequest(BaseModel):
    skillName: str = Field(..., example="Advanced Python Learning")
    structuredTasks: List[Task]

class IntegratePlanResponse(BaseModel):
    message: str
    calendarEventLinks: Optional[List[str]] = None


# --- API Endpoints ---

def get_planner_service():
    if planner_service_instance is None:
        raise HTTPException(
            status_code=503, 
            detail="Planner service is not available due to a startup configuration error. Please check server logs."
        )
    return planner_service_instance


@app.post("/chat-message", response_model=ChatMessageResponse, tags=["Chat"])
async def handle_chat_endpoint(request: ChatMessageRequest, planner: Any = Depends(get_planner_service)):
    """
    Handles a user's chat message and returns the AI's conversational response.
    """
    # Convert Pydantic GeminiContent models to simple dicts for the service
    history_as_dicts = [item.model_dump() for item in request.chatHistory]
    
    ai_response_text = planner.handle_chat_message(
        user_message=request.userMessage,
        chat_history=history_as_dicts
    )
    return ChatMessageResponse(aiResponse=ai_response_text)


@app.post("/generate-plan", response_model=GeneratePlanResponse, tags=["Planning"])
async def generate_plan_endpoint(request: GeneratePlanRequest, planner: Any = Depends(get_planner_service)):
    """
    Generates or refines a learning plan based on provided details and conversational context.
    """
    history_as_dicts = [item.model_dump() for item in request.chatHistoryForContext] if request.chatHistoryForContext else None
    existing_tasks_as_dicts = [task.model_dump() for task in request.existingPlanTasksForRefinement] if request.existingPlanTasksForRefinement else None

    structured_tasks_list, human_plan_or_error = planner.generate_structured_plan(
        goal=request.goal,
        duration_days=request.durationDays,
        start_date_str=request.startDate,
        learning_style=request.learningStyle,
        preferred_time_str=request.preferredTime,
        daily_hours=request.dailyHours,
        chat_history_for_context=history_as_dicts,
        refinement_instruction=request.refinementInstruction,
        existing_plan_tasks_for_refinement=existing_tasks_as_dicts
    )

    if structured_tasks_list is None:
        # human_plan_or_error contains the error message from the service
        raise HTTPException(status_code=400, detail=human_plan_or_error) 
        # Using 400 for "bad request" if plan generation failed due to input or AI inability,
        # or 500 if it was an internal server error (service should distinguish if possible)

    # Convert dicts back to Task Pydantic models for response validation
    validated_tasks = [Task(**task_data) for task_data in structured_tasks_list]
    return GeneratePlanResponse(humanReadablePlan=human_plan_or_error, structuredTasks=validated_tasks)


@app.post("/integrate-plan", response_model=IntegratePlanResponse, tags=["Calendar Integration"])
async def integrate_plan_endpoint(request: IntegratePlanRequest, planner: Any = Depends(get_planner_service)):
    """
    Integrates the provided structured tasks into the user's primary Google Calendar.
    """
    tasks_as_dicts = [task.model_dump() for task in request.structuredTasks]
    message, links = planner.add_plan_to_calendar(
        skill_name=request.skillName,
        structured_tasks=tasks_as_dicts
    )
    if "Successfully" not in message and "failed" in message.lower(): # Basic error check from service message
        raise HTTPException(status_code=500, detail=message)
        
    return IntegratePlanResponse(message=message, calendarEventLinks=links)


@app.get("/", tags=["General"])
async def root():
    service_status = "available" if planner_service_instance else "unavailable (startup error)"
    return {
        "message": "Welcome to the Learning Plan Generator API!",
        "service_status": service_status,
        "docs_url": "/docs"
    }

# To run this (after installing FastAPI, Uvicorn, Pydantic, etc.):
# 1. Ensure `planner_service.py` is in the same directory or Python path.
# 2. Ensure `.env` file with GOOGLE_API_KEY is present.
# 3. Ensure `credentials.json` is present.
# 4. If `token.json` does not exist or is invalid for the server environment,
#    you might need to generate it once manually (e.g., using a part of main_cli.py or a separate script)
#    and ensure the server process can read/write it if refresh is needed.
#    For production, consider service account credentials if user-specific calendar isn't the target.
#
# Command: uvicorn main_api:app --reload --port 8000