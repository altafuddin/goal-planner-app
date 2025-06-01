"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Send, CalendarIcon, Bot, User, Plus } from "lucide-react"
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
import { useAuth } from "@/lib/auth-context"
import { toast } from "@/components/ui/use-toast"
import { useCalendarStore } from "@/lib/calendar-store"

// Define the structure for a plan task
export interface PlanTask {
  id: string
  title: string
  description: string
  date: string
  startTime: string
  endTime: string
  priority: "high" | "medium" | "low"
}

// Define the structure for a complete plan
export interface Plan {
  id: string
  title: string
  description: string
  tasks: PlanTask[]
}

interface Message {
  id: string
  content: string
  sender: "user" | "ai"
  timestamp: Date
  plan?: Plan
}

// Mock responses based on keywords
const getMockResponse = (message: string): { content: string; plan?: Plan } => {
  const lowerMessage = message.toLowerCase()

  if (lowerMessage.includes("plan") || lowerMessage.includes("schedule") || lowerMessage.includes("create")) {
    // Generate a sample plan
    const today = new Date()
    const tomorrow = new Date(today)
    tomorrow.setDate(tomorrow.getDate() + 1)
    const dayAfter = new Date(today)
    dayAfter.setDate(dayAfter.getDate() + 2)

    const plan: Plan = {
      id: `plan-${Date.now()}`,
      title: "Productivity Plan",
      description: "A structured plan to help you achieve your goals efficiently.",
      tasks: [
        {
          id: "task-1",
          title: "Morning Planning Session",
          description: "Review goals and plan the day ahead",
          date: today.toISOString().split("T")[0],
          startTime: "09:00",
          endTime: "09:30",
          priority: "high",
        },
        {
          id: "task-2",
          title: "Focus Work Block",
          description: "Dedicated time for deep work on main objectives",
          date: today.toISOString().split("T")[0],
          startTime: "10:00",
          endTime: "12:00",
          priority: "high",
        },
        {
          id: "task-3",
          title: "Progress Review",
          description: "Assess progress and adjust plans as needed",
          date: tomorrow.toISOString().split("T")[0],
          startTime: "14:00",
          endTime: "14:30",
          priority: "medium",
        },
        {
          id: "task-4",
          title: "Skill Development",
          description: "Time dedicated to learning and skill improvement",
          date: dayAfter.toISOString().split("T")[0],
          startTime: "16:00",
          endTime: "17:00",
          priority: "medium",
        },
      ],
    }

    return {
      content: `✨ I've created a "${plan.title}" for you with ${plan.tasks.length} tasks. This plan will help you stay organized and productive!`,
      plan: plan,
    }
  }

  // Simple keyword-based responses
  if (lowerMessage.includes("hello") || lowerMessage.includes("hi")) {
    return {
      content:
        "👋 Hello! I'm your task management assistant. I can help you create plans, organize tasks, and manage your schedule. Try asking me to create a plan for something you'd like to accomplish!",
    }
  }

  if (lowerMessage.includes("task") || lowerMessage.includes("todo")) {
    return {
      content:
        "📋 I can help you manage tasks! You can use the calendar view to organize your schedule, create new tasks, and track your progress. Would you like me to create a plan for a specific goal?",
    }
  }

  if (lowerMessage.includes("help")) {
    return {
      content:
        "🚀 I'm here to help you stay organized! Here's what I can do:\n\n• ✅ Create structured plans for your goals\n• 📅 Help organize your tasks and schedule\n• 💡 Provide productivity tips\n• ⏰ Assist with time management\n\nTry asking me to 'create a plan for [your goal]' to get started!",
    }
  }

  if (lowerMessage.includes("calendar")) {
    return {
      content:
        "📅 The calendar feature lets you view your tasks in daily, weekly, and monthly formats. You can see upcoming events, mark tasks as complete, and get a clear overview of your schedule. Use the navigation at the top to switch between different calendar views!",
    }
  }

  if (lowerMessage.includes("productivity") || lowerMessage.includes("tips")) {
    return {
      content:
        "💪 Here are some productivity tips:\n\n• 🎯 Break large goals into smaller, manageable tasks\n• ⏱️ Use time blocking to focus on important work\n• 🏷️ Set priorities (high, medium, low) for your tasks\n• 🔄 Review and adjust your plans regularly\n• ☕ Take breaks to maintain focus and energy\n\nWould you like me to create a productivity plan for you?",
    }
  }

  // Default response
  return {
    content:
      "🤖 I'm your task management assistant! I can help you create plans, organize tasks, and manage your schedule. Try asking me to create a plan for something specific, or ask for help with productivity tips. What would you like to work on today?",
  }
}

export default function ChatInterface() {
  const { userInfo } = useAuth()
  const { addTasks } = useCalendarStore()
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      content:
        "👋 Hello! I'm your task management assistant. I can help you create plans, organize tasks, and manage your schedule. Try asking me to create a plan for a goal you have!",
      sender: "ai",
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState("")
  const [currentPlan, setCurrentPlan] = useState<Plan | null>(null)
  const [showPlanDialog, setShowPlanDialog] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector("[data-radix-scroll-area-viewport]")
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight
      }
    }
  }, [messages])

  const handleSendMessage = () => {
    if (!input.trim()) return

    // Create the user message
    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      sender: "user",
      timestamp: new Date(),
    }

    // Add the user message to the chat
    setMessages((prev) => [...prev, userMessage])

    // Get mock response
    const response = getMockResponse(input)

    // Create the AI message
    const aiMessage: Message = {
      id: (Date.now() + 1).toString(),
      content: response.content,
      sender: "ai",
      timestamp: new Date(),
      plan: response.plan,
    }

    // Add the AI message after a short delay
    setTimeout(() => {
      setMessages((prev) => [...prev, aiMessage])

      // If there's a plan, show the dialog
      if (response.plan) {
        setCurrentPlan(response.plan)
        setTimeout(() => {
          setShowPlanDialog(true)
        }, 500)
      }
    }, 1000)

    // Clear the input
    setInput("")
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleIntegratePlan = (plan: Plan) => {
    // Convert plan tasks to calendar tasks and add them to the store
    const calendarTasks = plan.tasks.map((task) => ({
      title: task.title,
      description: task.description,
      date: task.date,
      startTime: task.startTime,
      endTime: task.endTime,
      priority: task.priority,
      type: "task" as const,
    }))

    // Add all tasks to the calendar store
    addTasks(calendarTasks)

    // Show success message
    toast({
      title: "Plan Integrated Successfully!",
      description: `${plan.tasks.length} tasks have been added to your calendar and are now visible in your daily, weekly, and monthly views.`,
    })

    setShowPlanDialog(false)
  }

  return (
    <>
      <Card className="h-[calc(100vh-5rem)] flex flex-col card-colorful card-hover shadow-lg">
        <CardHeader className="px-4 py-3 border-b border-slate-200">
          <CardTitle className="text-lg font-bold flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-green-500 flex items-center justify-center">
              <Bot className="h-4 w-4 text-white" />
            </div>
            <span className="text-green-600">AI Assistant</span>
          </CardTitle>
        </CardHeader>
        <ScrollArea ref={scrollAreaRef} className="flex-1">
          <CardContent className="p-4 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"} animate-fade-in`}
              >
                <div
                  className={`flex items-start gap-3 max-w-[90%] ${message.sender === "user" ? "flex-row-reverse" : ""}`}
                >
                  <Avatar className="h-8 w-8 flex-shrink-0 shadow-md">
                    <AvatarFallback
                      className={`text-xs font-semibold ${
                        message.sender === "ai" ? "bg-green-500 text-white" : "bg-purple-500 text-white"
                      }`}
                    >
                      {message.sender === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                    </AvatarFallback>
                  </Avatar>
                  <div
                    className={`rounded-2xl px-4 py-3 text-sm transition-all duration-200 shadow-sm ${
                      message.sender === "user" ? "bg-purple-500 text-white" : "bg-white border border-slate-200"
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{message.content}</div>
                    {message.plan && (
                      <div className="mt-3 flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-xs bg-white/90 hover:bg-white border-slate-200 hover:border-blue-300"
                          onClick={() => {
                            setCurrentPlan(message.plan!)
                            setShowPlanDialog(true)
                          }}
                        >
                          <CalendarIcon className="h-3 w-3 mr-1" />
                          View Plan
                        </Button>
                        <Button
                          size="sm"
                          className="text-xs btn-blue"
                          onClick={() => handleIntegratePlan(message.plan!)}
                        >
                          <Plus className="h-3 w-3 mr-1" />
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
          </CardContent>
        </ScrollArea>
        <CardFooter className="p-3 border-t border-slate-200">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSendMessage()
            }}
            className="flex w-full items-center space-x-2"
          >
            <Input
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              className="flex-1 h-10 text-sm bg-white border-slate-200 focus:border-purple-300 focus:ring-purple-200 rounded-xl"
            />
            <Button type="submit" size="sm" disabled={!input.trim()} className="btn-purple shadow-lg rounded-xl px-4">
              <Send className="h-4 w-4" />
              <span className="sr-only">Send message</span>
            </Button>
          </form>
        </CardFooter>
      </Card>

      {/* Plan Dialog */}
      <Dialog open={showPlanDialog} onOpenChange={setShowPlanDialog}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-auto card-colorful">
          <DialogHeader>
            <DialogTitle className="text-purple-600 text-xl">{currentPlan?.title || "Plan Details"}</DialogTitle>
            <DialogDescription className="text-slate-600">{currentPlan?.description}</DialogDescription>
          </DialogHeader>

          <div className="space-y-4 my-4">
            <h3 className="text-lg font-semibold text-slate-700">Tasks</h3>
            <div className="space-y-3">
              {currentPlan?.tasks.map((task) => (
                <Card key={task.id} className="p-4 card-colorful card-hover border border-slate-200">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-semibold text-slate-800">{task.title}</h4>
                      <p className="text-sm text-slate-600 mt-1">{task.description}</p>
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
                      {new Date(task.date).toLocaleDateString()} • {task.startTime} - {task.endTime}
                    </span>
                  </div>
                </Card>
              ))}
            </div>
          </div>

          <DialogFooter className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => setShowPlanDialog(false)}
              className="bg-white hover:bg-slate-50 border-slate-200"
            >
              Close
            </Button>
            <Button onClick={() => currentPlan && handleIntegratePlan(currentPlan)} className="btn-blue">
              <Plus className="h-4 w-4 mr-2" />
              Integrate to Calendar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
