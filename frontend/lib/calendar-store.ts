"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"

// --- Define the Backend Task Interface (matches FastAPI's Task model) ---
// You likely already have this in your frontend types or can add it.
// This is the shape of the data coming from your backend.
export interface BackendTask {
  summary: string
  description?: string | null // Nullable for backend, so use `| null`
  startTime: string // ISO 8601 datetime string (e.g., "2023-10-27T09:00:00")
  endTime: string   // ISO 8601 datetime string
}

// --- Your Existing CalendarTask Interface ---
export interface CalendarTask {
  id: string
  title: string
  description: string
  date: string // YYYY-MM-DD
  startTime: string // HH:MM
  endTime: string // HH:MM
  priority: "high" | "medium" | "low"
  completed: boolean
  type: "task" | "event"
  location?: string
  attendees?: number
}

interface CalendarStore {
  tasks: CalendarTask[]
  addTask: (task: Omit<CalendarTask, "id" | "completed">) => void
  // Modify addTasks to accept BackendTask[] and transform them
  addBackendTasks: (backendTasks: BackendTask[]) => void // New method for backend integration
  toggleTask: (id: string) => void
  deleteTask: (id: string) => void
  updateTask: (id: string, updates: Partial<CalendarTask>) => void
  getTasksForDate: (date: string) => CalendarTask[]
  getTasksForDateRange: (startDate: string, endDate: string) => CalendarTask[]
}

export const useCalendarStore = create<CalendarStore>()(
  persist(
    (set, get) => ({
      tasks: [
        // Your default tasks remain here
        {
          id: "default-1",
          title: "Team meeting",
          description: "Discuss project timeline and deliverables",
          date: new Date().toISOString().split("T")[0],
          startTime: "10:00",
          endTime: "11:00",
          priority: "high",
          completed: false,
          type: "task",
        },
        {
          id: "default-2",
          title: "Review designs",
          description: "Go through the latest UI mockups",
          date: new Date().toISOString().split("T")[0],
          startTime: "14:00",
          endTime: "15:00",
          priority: "medium",
          completed: true,
          type: "task",
        },
        {
          id: "default-3",
          title: "Code review",
          description: "Review pull requests from the team",
          date: new Date().toISOString().split("T")[0],
          startTime: "16:00",
          endTime: "17:00",
          priority: "low",
          completed: false,
          type: "task",
        },
      ],

      addTask: (task) => {
        const newTask: CalendarTask = {
          ...task,
          id: `task-${Date.now()}-${Math.random().toString(36).substring(7)}`,
          completed: false,
        }
        set((state) => ({
          tasks: [...state.tasks, newTask],
        }))
      },

      // --- NEW METHOD: addBackendTasks ---
      addBackendTasks: (backendTasks: BackendTask[]) => {
        const newCalendarTasks: CalendarTask[] = backendTasks.map((bTask) => {
          // Parse the ISO 8601 datetime strings
          const startDateTime = new Date(bTask.startTime);
          const endDateTime = new Date(bTask.endTime);

          return {
            id: `plan-${Date.now()}-${Math.random().toString(36).substring(7)}`, // Generate unique ID
            title: bTask.summary,
            description: bTask.description || "", // Ensure description is a string
            date: startDateTime.toISOString().split('T')[0], // Extract YYYY-MM-DD
            startTime: startDateTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }), // Extract HH:MM
            endTime: endDateTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }),   // Extract HH:MM
            priority: "medium", // Default for AI-generated tasks
            completed: false,
            type: "task", // Default for AI-generated tasks
            // location and attendees can be omitted or defaulted
          };
        });

        set((state) => ({
          tasks: [...state.tasks, ...newCalendarTasks],
        }));
      },

      // You can keep `addTasks` if you use it elsewhere for tasks that don't need transformation,
      // but if all new tasks come through the backend, you might only need `addBackendTasks`.
      // For clarity, I'm removing the original `addTasks` as it's less direct for backend integration.
      // If you need it for other non-backend task additions, uncomment the original `addTasks` above.

      addTasks: (tasks: Omit<CalendarTask, "id" | "completed">[]): void => {
        const newTasks: CalendarTask[] = tasks.map((task: Omit<CalendarTask, "id" | "completed">, index: number) => ({
          ...task,
          id: `task-${Date.now()}-${index}-${Math.random().toString(36).substring(7)}`,
          completed: false,
        }))
        set((state: CalendarStore) => ({
          tasks: [...state.tasks, ...newTasks],
        }))
      },

      toggleTask: (id: string): void => {
        set((state) => ({
          tasks: state.tasks.map((task) => (task.id === id ? { ...task, completed: !task.completed } : task)),
        }))
      },

      deleteTask: (id) => {
        set((state) => ({
          tasks: state.tasks.filter((task) => task.id !== id),
        }))
      },

      updateTask: (id, updates) => {
        set((state) => ({
          tasks: state.tasks.map((task) => (task.id === id ? { ...task, ...updates } : task)),
        }))
      },

      getTasksForDate: (date) => {
        return get().tasks.filter((task) => task.date === date)
      },

      getTasksForDateRange: (startDate, endDate) => {
        return get().tasks.filter((task) => task.date >= startDate && task.date <= endDate)
      },
    }),
    {
      name: "calendar-storage",
    },
  ),
)
