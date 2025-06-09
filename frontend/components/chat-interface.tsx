"use client"

import type React from "react"
import { useState, useRef, useEffect } from "react"
import { Send, CalendarIcon, Bot, User, Plus, Loader2, RefreshCw } from "lucide-react" // Added RefreshCw
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { toast } from "@/components/ui/use-toast"
import { useCalendarStore } from "@/lib/calendar-store" // For local calendar UI updates
import { Textarea } from "@/components/ui/textarea" // Added for refinement

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// --- Type Definitions for API Interaction ---

// Matches backend Pydantic model for chat history
interface BackendGeminiContentPart {
  text: string;
}
interface BackendGeminiContent {
  role: "user" | "model";
  parts: BackendGeminiContentPart[];
}

// Matches backend's Task model (in GeneratePlanResponse and IntegratePlanRequest)
interface BackendTask {
  summary: string;
  description?: string | null; // Ensure it can be null
  startTime: string; // ISO format string
  endTime: string;    // ISO format string
}

// For GeneratePlanRequest payload (subset for example)
interface GeneratePlanRequestPayload {
  goal: string;
  durationDays: number;
  startDate: string; // YYYY-MM-DD
  learningStyle?: string;
  preferredTime?: string;
  dailyHours?: number;
  chatHistoryForContext?: BackendGeminiContent[];
  // For refinement (optional)
  refinementInstruction?: string;
  existingPlanTasksForRefinement?: BackendTask[];
}

// For displaying tasks in the UI (can be richer than BackendTask)
export interface UITask {
  id: string; // Frontend generated for keys
  title: string;
  description: string | null;
  date: string; // Extracted for display
  startTime: string; // Extracted for display
  endTime: string; // Extracted for display
  priority: "high" | "medium" | "low"; // Frontend specific
  // Original backend task can be stored if needed for precise re-submission
  backendTask?: BackendTask;
}

// For displaying the plan in the UI
export interface UIPlan {
  title: string; // Could be the 'goal' or from humanReadablePlan
  description?: string; // From humanReadablePlan or a summary
  tasks: UITask[];
  humanReadablePlan?: string; // Store the human-readable string from backend
  originalBackendTasks?: BackendTask[]; // Store original tasks for integration
  // Store original request parameters to re-use for refinement
  originalRequestParams?: Partial<GeneratePlanRequestPayload>;
}

interface FrontendMessage {
  id: string;
  text: string;
  role: "user" | "ai";
  timestamp: Date;
}

export default function ChatInterface() {
  const { addBackendTasks } = useCalendarStore(); // Changed from addTasks to addBackendTasks

  const [messages, setMessages] = useState<FrontendMessage[]>([
    {
      id: "1",
      text: "👋 Hello! I'm your AI assistant. Tell me about a skill you'd like to learn, for how long, and when you'd like to start. For example: 'I want to learn FastAPI in 2 days, starting tomorrow'.",
      role: "ai",
      timestamp: new Date(),
    },
  ]);
  const [chatInput, setChatInput] = useState("");

  const [currentGeneratedPlan, setCurrentGeneratedPlan] = useState<UIPlan | null>(null);
  const [isPlanDialogOpen, setIsPlanDialogOpen] = useState(false);
  const [refinementInput, setRefinementInput] = useState(""); // For plan refinement

  const [isChatting, setIsChatting] = useState(false);
  const [isGeneratingPlan, setIsGeneratingPlan] = useState(false);
  const [isIntegratingPlan, setIsIntegratingPlan] = useState(false);

  // Store the last collected parameters for plan generation
  const [planRequestParams, setPlanRequestParams] = useState<Partial<GeneratePlanRequestPayload>>({});

  const scrollAreaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector("[data-radix-scroll-area-viewport]");
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    }
  }, [messages]);

  const mapMessagesToBackendHistory = (msgs: FrontendMessage[]): BackendGeminiContent[] => {
    return msgs.map(m => ({
      role: m.role === "ai" ? "model" : "user",
      parts: [{ text: m.text }],
    }));
  };

  const mapBackendTaskToUITask = (task: BackendTask, index: number): UITask => {
    const startDate = new Date(task.startTime);
    return {
      id: `task-${index}-${Date.now()}`,
      title: task.summary,
      description: task.description || null,
      date: startDate.toISOString().split("T")[0],
      startTime: startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }),
      endTime: new Date(task.endTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }),
      priority: "medium", // Default priority, frontend can manage this
      backendTask: task,
    };
  };

  // Helper to parse potential plan parameters from user's chat message
  const parsePlanParamsFromMessage = (message: string): Partial<GeneratePlanRequestPayload> => {
    const params: Partial<GeneratePlanRequestPayload> = {};

    // Example regex to extract details (this can be improved for robustness)
    const goalMatch = message.match(/(learn|master|understand)\s+([a-zA-Z0-9\s]+?)(?:\s+in\s+(\d+)\s+days|\s+starting|\s*$)/i);
    if (goalMatch && goalMatch[2]) {
      params.goal = goalMatch[2].trim();
    }

    const durationMatch = message.match(/(\d+)\s+(day|week|month)s?/i);
    if (durationMatch && durationMatch[1] && durationMatch[2]) {
      let duration = parseInt(durationMatch[1], 10);
      if (durationMatch[2].toLowerCase().startsWith("week")) {
        duration *= 7;
      } else if (durationMatch[2].toLowerCase().startsWith("month")) {
        duration *= 30; // Approximation
      }
      params.durationDays = duration;
    }

    // Very basic date parsing (e.g., "tomorrow", "next week", "YYYY-MM-DD")
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(today.getDate() + 1);

    const startDateMatch = message.match(/(starting|start)\s+(tomorrow|today|next week|next monday|(\d{4}-\d{2}-\d{2}))/i);
    if (startDateMatch) {
      const dateStr = startDateMatch[2].toLowerCase();
      if (dateStr === "tomorrow") {
        params.startDate = tomorrow.toISOString().split("T")[0];
      } else if (dateStr === "today") {
        params.startDate = today.toISOString().split("T")[0];
      } else if (dateStr === "next week" || dateStr === "next monday") {
        const nextMonday = new Date(today);
        nextMonday.setDate(today.getDate() + (1 + 7 - today.getDay()) % 7); // Calculate next Monday
        params.startDate = nextMonday.toISOString().split("T")[0];
      } else if (dateStr.match(/^\d{4}-\d{2}-\d{2}$/)) {
        params.startDate = dateStr;
      }
    } else {
      // Default to tomorrow if no specific date is mentioned
      params.startDate = tomorrow.toISOString().split("T")[0];
    }

    const dailyHoursMatch = message.match(/(\d+(\.\d+)?)\s+hours?\s+daily/i);
    if (dailyHoursMatch && dailyHoursMatch[1]) {
      params.dailyHours = parseFloat(dailyHoursMatch[1]);
    }

    // Update global plan request parameters based on parsing
    setPlanRequestParams(prev => ({ ...prev, ...params }));

    return params;
  };


  // 1. Send User Messages (/chat-message)
  const handleSendMessage = async () => {
    if (!chatInput.trim()) return;

    const newUserMessage: FrontendMessage = {
      id: Date.now().toString(),
      text: chatInput,
      role: "user",
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, newUserMessage]);
    const currentInput = chatInput;
    setChatInput("");
    setIsChatting(true);

    // Attempt to parse parameters from the user's message
    parsePlanParamsFromMessage(currentInput);

    const backendChatHistory = mapMessagesToBackendHistory([...messages, newUserMessage]);

    try {
      const response = await fetch(`${API_BASE_URL}/chat-message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userMessage: currentInput,
          chatHistory: backendChatHistory.slice(0, -1) // Send history *before* current message
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to get response from AI");
      }

      const data: { aiResponse: string } = await response.json();
      const aiResponseMessage: FrontendMessage = {
        id: (Date.now() + 1).toString(),
        text: data.aiResponse,
        role: "ai",
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiResponseMessage]);

      // If the AI's response indicates readiness to generate a plan, show a toast
      if (data.aiResponse.toLowerCase().includes("ready to generate") || data.aiResponse.toLowerCase().includes("shall i create the plan")) {
        toast({ title: "AI is ready to plan!", description: "You can now click 'Generate/Refine Plan' or refine your request." });
      }

    } catch (error) {
      console.error("Chat API error:", error);
      toast({ title: "Error", description: (error as Error).message, variant: "destructive" });
      const errorResponseMessage: FrontendMessage = {
        id: (Date.now() + 1).toString(),
        text: `Sorry, I encountered an error: ${(error as Error).message}`,
        role: "ai",
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorResponseMessage]);
    } finally {
      setIsChatting(false);
    }
  };

  // 2. Generate Plan (/generate-plan)
  const handleRequestPlanGeneration = async (refinementInstruction?: string) => {
    // Use either last captured params or defaults if not set
    const payload: GeneratePlanRequestPayload = {
      goal: planRequestParams.goal || "Learning Goal", // Default fallback if not parsed
      durationDays: planRequestParams.durationDays || 7, // Default fallback
      startDate: planRequestParams.startDate || new Date(Date.now() + 86400000).toISOString().split("T")[0], // Tomorrow
      dailyHours: planRequestParams.dailyHours || 2, // Default fallback
      learningStyle: planRequestParams.learningStyle,
      preferredTime: planRequestParams.preferredTime,
      chatHistoryForContext: mapMessagesToBackendHistory(messages),
      ...(refinementInstruction && currentGeneratedPlan && {
        refinementInstruction: refinementInstruction,
        existingPlanTasksForRefinement: currentGeneratedPlan.originalBackendTasks
      })
    };

    if (!payload.goal || !payload.durationDays || !payload.startDate) {
      toast({ title: "Missing Details", description: "Please specify a goal, duration (in days), and start date for the plan.", variant: "destructive" });
      return;
    }

    setIsGeneratingPlan(true);
    setCurrentGeneratedPlan(null); // Clear previous plan during generation

    try {
      const response = await fetch(`${API_BASE_URL}/generate-plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to generate plan");
      }

      const data: { humanReadablePlan: string; structuredTasks: BackendTask[] } = await response.json();

      const newUIPlan: UIPlan = {
        title: payload.goal,
        description: `A plan to ${payload.goal} over ${payload.durationDays} days starting ${payload.startDate}.`,
        tasks: data.structuredTasks.map(mapBackendTaskToUITask),
        humanReadablePlan: data.humanReadablePlan,
        originalBackendTasks: data.structuredTasks,
        originalRequestParams: payload // Store original request params for future refinements
      };
      setCurrentGeneratedPlan(newUIPlan);

      const planIntroMessage: FrontendMessage = {
        id: (Date.now() + 10).toString(), // Ensure unique ID
        text: `Okay, I've generated a plan for you to "${payload.goal}". You can review it now!`,
        role: "ai",
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, planIntroMessage]);

      setTimeout(() => setIsPlanDialogOpen(true), 300);
      toast({ title: "Plan Generated!", description: "Your new learning plan is ready." });

    } catch (error) {
      console.error("Generate Plan API error:", error);
      toast({ title: "Error Generating Plan", description: (error as Error).message, variant: "destructive" });
    } finally {
      setIsGeneratingPlan(false);
      setRefinementInput(""); // Clear refinement input
    }
  };

  // 3. Integrate Plan (/integrate-plan)
  const handleIntegratePlanToCalendar = async () => {
    if (!currentGeneratedPlan || !currentGeneratedPlan.originalBackendTasks) {
      toast({ title: "No Plan", description: "No plan to integrate.", variant: "destructive" });
      return;
    }

    setIsIntegratingPlan(true);
    try {
      const payload = {
        skillName: currentGeneratedPlan.title,
        structuredTasks: currentGeneratedPlan.originalBackendTasks,
      };

      const response = await fetch(`${API_BASE_URL}/integrate-plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to integrate plan to Google Calendar");
      }

      const data: { message: string; calendarEventLinks?: string[] } = await response.json();
      toast({ title: "Plan Integrated!", description: data.message });

      // This leverages the transformation logic already in lib/calendar-store.ts
      addBackendTasks(currentGeneratedPlan.originalBackendTasks);

      setIsPlanDialogOpen(false);
      setCurrentGeneratedPlan(null); // Optionally clear plan after integration

    } catch (error) {
      console.error("Integrate Plan API error:", error);
      toast({ title: "Error Integrating Plan", description: (error as Error).message, variant: "destructive" });
    } finally {
      setIsIntegratingPlan(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleRefinePlan = () => {
    if (!refinementInput.trim()) {
      toast({ title: "Refinement Empty", description: "Please type your refinement instructions.", variant: "destructive" });
      return;
    }
    if (!currentGeneratedPlan || !currentGeneratedPlan.originalRequestParams) {
      toast({ title: "No Plan to Refine", description: "A plan must be generated first.", variant: "destructive" });
      return;
    }

    // Re-use original parameters and add refinement instruction
    // Ensure all required fields are present and not undefined
    const originalParams = currentGeneratedPlan.originalRequestParams || {};
    if (
      !originalParams.goal ||
      !originalParams.durationDays ||
      !originalParams.startDate
    ) {
      toast({ title: "Missing Plan Details", description: "Cannot refine plan: missing goal, duration, or start date.", variant: "destructive" });
      return;
    }
    const paramsForRefinement: GeneratePlanRequestPayload = {
      goal: originalParams.goal,
      durationDays: originalParams.durationDays,
      startDate: originalParams.startDate,
      learningStyle: originalParams.learningStyle,
      preferredTime: originalParams.preferredTime,
      dailyHours: originalParams.dailyHours,
      refinementInstruction: refinementInput,
      existingPlanTasksForRefinement: currentGeneratedPlan.originalBackendTasks,
      chatHistoryForContext: mapMessagesToBackendHistory(messages)
    };
    handleRequestPlanGeneration(paramsForRefinement.refinementInstruction); // Pass refinement instruction
    setIsPlanDialogOpen(false); // Close dialog while regenerating
  };


  // Example: Button to trigger plan generation
  const renderPlanGenerationButton = () => {
    // This button acts as a trigger for both initial generation and refinement
    const isReadyForInitialPlan = planRequestParams.goal && planRequestParams.durationDays && planRequestParams.startDate;
    const buttonText = currentGeneratedPlan ? "Refine Current Plan" : (isReadyForInitialPlan ? "Generate Plan" : "Generate Plan (needs details)");

    return (
      <Button
        onClick={() => {
          // If a plan exists, we're explicitly trying to refine it.
          // The refinement instruction would ideally come from a separate input
          // in the dialog or chat. For now, we'll assume the dialog's refinement input.
          // If no plan, we try to generate based on collected params.
          if (currentGeneratedPlan) {
            setIsPlanDialogOpen(true); // Open dialog to allow refinement input
          } else {
            handleRequestPlanGeneration(); // Initial generation
          }
        }}
        disabled={isGeneratingPlan || isChatting || (!currentGeneratedPlan && !isReadyForInitialPlan)}
        variant="outline"
        size="sm"
        className="m-2"
      >
        {isGeneratingPlan ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : (currentGeneratedPlan ? <RefreshCw className="mr-2 h-4 w-4" /> : <Plus className="mr-2 h-4 w-4" />)}
        {buttonText}
      </Button>
    );
  };

  return (
    <>
      <Card className="h-[calc(100vh-5rem)] flex flex-col card-colorful card-hover shadow-lg">
        <CardHeader className="px-4 py-3 border-b border-slate-200 flex justify-between items-center">
          <CardTitle className="text-lg font-bold flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-green-500 flex items-center justify-center">
              <Bot className="h-4 w-4 text-white" />
            </div>
            <span className="text-green-600">AI Assistant</span>
          </CardTitle>
          {renderPlanGenerationButton()}
        </CardHeader>
        <ScrollArea ref={scrollAreaRef} className="flex-1">
          <CardContent className="p-4 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"} animate-fade-in`}
              >
                <div
                  className={`flex items-start gap-3 max-w-[90%] ${message.role === "user" ? "flex-row-reverse" : ""}`}
                >
                  <Avatar className="h-8 w-8 flex-shrink-0 shadow-md">
                    <AvatarFallback
                      className={`text-xs font-semibold ${message.role === "ai" ? "bg-green-500 text-white" : "bg-purple-500 text-white"
                        }`}
                    >
                      {message.role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                    </AvatarFallback>
                  </Avatar>
                  <div
                    className={`rounded-2xl px-4 py-3 text-sm transition-all duration-200 shadow-sm ${message.role === "user" ? "bg-purple-500 text-white" : "bg-white border border-slate-200"
                      }`}
                  >
                    <div className="whitespace-pre-wrap">{message.text}</div>
                    {message.role === "ai" && currentGeneratedPlan && message.text.includes(currentGeneratedPlan.title) && (
                      <div className="mt-3 flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-xs bg-white/90 hover:bg-white border-slate-200 hover:border-blue-300"
                          onClick={() => setIsPlanDialogOpen(true)}
                        >
                          <CalendarIcon className="h-3 w-3 mr-1" /> View Plan
                        </Button>
                        <Button
                          size="sm"
                          className="text-xs btn-blue"
                          onClick={handleIntegratePlanToCalendar}
                          disabled={isIntegratingPlan}
                        >
                          {isIntegratingPlan ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Plus className="h-3 w-3 mr-1" />}
                          Integrate
                        </Button>
                      </div>
                    )}
                    <div className="text-xs opacity-70 mt-2">
                      {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </div>
                  </div>
                </div>
              </div>
            ))}
            {(isChatting || isGeneratingPlan) && (
              <div className="flex justify-center items-center p-2">
                <Loader2 className="h-5 w-5 text-slate-400 animate-spin" />
                <span className="ml-2 text-sm text-slate-500">
                  {isChatting ? "AI is thinking..." : isGeneratingPlan ? "Generating plan..." : ""}
                </span>
              </div>
            )}
          </CardContent>
        </ScrollArea>
        <CardFooter className="p-3 border-t border-slate-200">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex w-full items-center space-x-2"
          >
            <Input
              placeholder="Type your message, or ask to generate a plan..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyPress={handleKeyPress}
              className="flex-1 h-10 text-sm bg-white border-slate-200 focus:border-purple-300 focus:ring-purple-200 rounded-xl"
              disabled={isChatting || isGeneratingPlan}
            />
            <Button type="submit" size="sm" disabled={!chatInput.trim() || isChatting || isGeneratingPlan} className="btn-purple shadow-lg rounded-xl px-4">
              {isChatting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              <span className="sr-only">Send message</span>
            </Button>
          </form>
        </CardFooter>
      </Card>

      {/* Plan Dialog */}
      <Dialog open={isPlanDialogOpen} onOpenChange={setIsPlanDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto card-colorful">
          <DialogHeader>
            <DialogTitle className="text-purple-600 text-xl">{currentGeneratedPlan?.title || "Plan Details"}</DialogTitle>
            <DialogDescription className="text-slate-600">
              {currentGeneratedPlan?.description || "Review the tasks for your plan."}
            </DialogDescription>
            {currentGeneratedPlan?.humanReadablePlan && (
              <ScrollArea className="mt-2 p-2 border rounded-md max-h-40 bg-slate-50 text-sm text-slate-700">
                <h4 className="font-semibold mb-1">AI's Full Plan Outline:</h4>
                <pre className="whitespace-pre-wrap font-sans text-xs">{currentGeneratedPlan.humanReadablePlan}</pre>
              </ScrollArea>
            )}
          </DialogHeader>

          <div className="space-y-4 my-4">
            <h3 className="text-lg font-semibold text-slate-700">Tasks</h3>
            <div className="space-y-3">
              {currentGeneratedPlan?.tasks.map((task) => (
                <Card key={task.id} className="p-4 card-colorful card-hover border border-slate-200">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-semibold text-slate-800">{task.title}</h4>
                      {task.description && <p className="text-sm text-slate-600 mt-1">{task.description}</p>}
                    </div>
                    <Badge
                      variant={
                        task.priority === "high" ? "destructive" : task.priority === "medium" ? "default" : "secondary"
                      }
                      className="font-medium"
                    >
                      {task.priority}
                    </Badge>
                  </div>
                  <div className="mt-3 flex items-center text-sm text-slate-500">
                    <CalendarIcon className="h-4 w-4 mr-2" />
                    <span>
                      {new Date(task.date).toLocaleDateString(undefined, { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' })} • {task.startTime} - {task.endTime}
                    </span>
                  </div>
                </Card>
              ))}
              {(!currentGeneratedPlan || currentGeneratedPlan.tasks.length === 0) && (
                <p className="text-slate-500">No tasks in this plan yet.</p>
              )}
            </div>
          </div>

          {/* Refinement Section */}
          {currentGeneratedPlan && (
            <div className="mt-6 pt-4 border-t border-slate-100">
              <h3 className="text-md font-semibold text-slate-700 mb-2">Refine Plan:</h3>
              <Textarea
                placeholder="e.g., 'Make day 3 focus more on project work', 'Increase daily hours to 3', 'Shift all tasks to evening'"
                value={refinementInput}
                onChange={(e) => setRefinementInput(e.target.value)}
                rows={3}
                className="mb-3"
              />
              <Button
                onClick={handleRefinePlan}
                disabled={isGeneratingPlan || !refinementInput.trim()}
                className="btn-purple"
              >
                {isGeneratingPlan ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-2" />}
                Regenerate with Refinement
              </Button>
            </div>
          )}


          <DialogFooter className="flex gap-2 mt-4">
            <Button
              variant="outline"
              onClick={() => setIsPlanDialogOpen(false)}
              className="bg-white hover:bg-slate-50 border-slate-200"
            >
              Close
            </Button>
            <Button
              onClick={handleIntegratePlanToCalendar}
              className="btn-blue"
              disabled={isIntegratingPlan || !currentGeneratedPlan || currentGeneratedPlan.tasks.length === 0}
            >
              {isIntegratingPlan ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Plus className="h-4 w-4 mr-2" />}
              Integrate to Calendar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}