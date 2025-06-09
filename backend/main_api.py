import os
import datetime
from typing import List, Dict, Any, Optional, Tuple

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import the LearningPlannerService class from your planner_service.py
from planner_service import LearningPlannerService
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env

# --- Configuration ---
origins = [
    "http://localhost:3000",
]

app = FastAPI(
    title="Learning Planner API",
    description="API for AI-powered learning plan generation and Google Calendar integration.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependency Injection for LearningPlannerService ---
# This will hold the single instance of the service
_planner_service_instance: Optional[LearningPlannerService] = None

def get_planner_service_instance() -> LearningPlannerService:
    """
    FastAPI dependency that returns a singleton instance of LearningPlannerService.
    Initializes it if it hasn't been already.
    """
    global _planner_service_instance
    if _planner_service_instance is None:
        try:
            _planner_service_instance = LearningPlannerService()
            print("LearningPlannerService instance created and initialized.")
        except Exception as e:
            print(f"Failed to initialize LearningPlannerService: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Backend service initialization failed. Check server logs. Error: {e}"
            )
    return _planner_service_instance


# --- Pydantic Models for API Request/Response Bodies ---

# Matches BackendGeminiContentPart from chat-interface.tsx
class GeminiContentPart(BaseModel):
    text: str

# Matches BackendGeminiContent from chat-interface.tsx
class GeminiContent(BaseModel):
    role: str # "user" or "model"
    parts: List[GeminiContentPart]

# For /chat-message endpoint
class ChatMessageRequest(BaseModel):
    userMessage: str
    chatHistory: List[GeminiContent] = Field(default_factory=list)

class ChatMessageResponse(BaseModel):
    aiResponse: str

# Matches BackendTask from chat-interface.tsx
class Task(BaseModel):
    summary: str
    description: Optional[str] = None # Can be null
    startTime: str # ISO format string (e.g., "2023-10-27T09:00:00")
    endTime: str   # ISO format string

# For /generate-plan endpoint request
class GeneratePlanRequest(BaseModel):
    goal: str
    durationDays: int
    startDate: str # YYYY-MM-DD
    learningStyle: Optional[str] = None
    preferredTime: Optional[str] = None
    dailyHours: Optional[float] = None
    chatHistoryForContext: List[GeminiContent] = Field(default_factory=list)

    # Fields for plan refinement
    refinementInstruction: Optional[str] = None
    existingPlanTasksForRefinement: Optional[List[Task]] = None # List of Task models

# For /generate-plan endpoint response
class GeneratePlanResponse(BaseModel):
    humanReadablePlan: str
    structuredTasks: List[Task]

# For /integrate-plan endpoint request
class IntegratePlanRequest(BaseModel):
    skillName: str
    structuredTasks: List[Task]

# For /integrate-plan endpoint response
class IntegratePlanResponse(BaseModel):
    message: str
    calendarEventLinks: Optional[List[str]] = None

# For /integrated-plan endpoint response (new for calendar-view.tsx)
class GetIntegratedPlanResponse(BaseModel):
    skillName: Optional[str] = None
    structuredTasks: List[Task] = Field(default_factory=list)
    calendarEventLinks: Optional[List[str]] = Field(default_factory=list)


# --- API Endpoints ---

@app.post("/chat-message", response_model=ChatMessageResponse, tags=["Chat"])
async def chat_message_endpoint(
    request: ChatMessageRequest,
    planner: LearningPlannerService = Depends(get_planner_service_instance) # Inject the service instance
):
    """
    Handles user chat messages and returns AI responses.
    Maintains chat history for context.
    """
    try:
        # Convert Pydantic models back to simple dicts for the service layer
        chat_history_dicts = [h.model_dump(mode='json') for h in request.chatHistory]
        ai_response_text = planner.handle_chat_message(request.userMessage, chat_history_dicts)
        return ChatMessageResponse(aiResponse=ai_response_text)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"Error in /chat-message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred while processing your chat message. Error: {e}"
        )

@app.post("/generate-plan", response_model=GeneratePlanResponse, tags=["Planning"])
async def generate_plan_endpoint(
    request: GeneratePlanRequest,
    planner: LearningPlannerService = Depends(get_planner_service_instance) # Inject the service instance
):
    """
    Generates a structured learning plan based on user input.
    Can also refine an existing plan.
    """
    try:
        # Prepare existing_plan_tasks_for_refinement if present
        existing_tasks_dicts = None
        if request.existingPlanTasksForRefinement:
            existing_tasks_dicts = [t.model_dump(mode='json') for t in request.existingPlanTasksForRefinement]

        # Convert chat_history_for_context from Pydantic models to plain dicts for the service
        chat_history_for_context_dicts = [h.model_dump(mode='json') for h in request.chatHistoryForContext]
        # print("Chat history for context:")
        structured_tasks, human_readable_plan = planner.generate_structured_plan(
            goal=request.goal,
            duration_days=request.durationDays,
            start_date_str=request.startDate,
            learning_style=request.learningStyle,
            preferred_time_str=request.preferredTime,
            daily_hours=request.dailyHours,
            chat_history_for_context=chat_history_for_context_dicts, # Pass as dicts
            refinement_instruction=request.refinementInstruction,
            existing_plan_tasks_for_refinement=existing_tasks_dicts # Pass as dicts
        )

        if structured_tasks is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=human_readable_plan # human_readable_plan contains the error message if None
            )

        # The planner service automatically updates its internal state (last_generated_plan_tasks etc.)

        return GeneratePlanResponse(
            humanReadablePlan=human_readable_plan,
            structuredTasks=structured_tasks
        )
    except HTTPException as e:
        raise e # Re-raise FastAPI HTTPExceptions
    except Exception as e:
        print(f"Error in /generate-plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred during plan generation. Error: {e}"
        )

@app.post("/integrate-plan", response_model=IntegratePlanResponse, tags=["Calendar Integration"])
async def integrate_plan_endpoint(
    request: IntegratePlanRequest,
    planner: LearningPlannerService = Depends(get_planner_service_instance) # Inject the service instance
):
    """
    Adds the generated learning plan tasks to Google Calendar.
    """
    try:
        # Convert Pydantic models back to simple dicts for the service layer
        structured_tasks_dicts = [t.model_dump(mode='json') for t in request.structuredTasks]
        message, event_links = planner.add_plan_to_calendar(request.skillName, structured_tasks_dicts)

        if event_links is None:
            # If no events were added, it's a client-side issue or specific error from service
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )

        # The planner service automatically updates its internal state (last_integrated_calendar_links etc.)

        return IntegratePlanResponse(
            message=message,
            calendarEventLinks=event_links
        )
    except HTTPException as e:
        raise e # Re-raise FastAPI HTTPExceptions
    except Exception as e:
        print(f"Error in /integrate-plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred during calendar integration. Error: {e}"
        )

@app.get("/integrated-plan", response_model=GetIntegratedPlanResponse, tags=["Calendar Integration"])
async def get_integrated_plan_endpoint(
    planner: LearningPlannerService = Depends(get_planner_service_instance) # Inject the service instance
):
    """
    Retrieves the most recently integrated plan for display in the calendar view.
    """
    structured_tasks, skill_name = planner.get_last_integrated_plan_for_display()
    calendar_links = planner.get_last_integrated_plan_calendar_links()

    if not structured_tasks:
        # If no plan has been generated/integrated yet or server restarted and lost state
        return GetIntegratedPlanResponse(
            skillName="No plan generated or integrated yet",
            structuredTasks=[],
            calendarEventLinks=[]
        )

    # Ensure tasks are returned as Task Pydantic models if they aren't already
    # (they should be coming from planner_service in correct dict format, so just cast)
    validated_tasks = [Task(**task_data) for task_data in structured_tasks]

    return GetIntegratedPlanResponse(
        skillName=skill_name,
        structuredTasks=validated_tasks,
        calendarEventLinks=calendar_links
    )

# --- Root Endpoint (Optional, for API health check) ---
@app.get("/", tags=["Health"])
async def read_root():
    """
    Basic health check endpoint.
    """
    return {"message": "Learning Planner API is running!"}