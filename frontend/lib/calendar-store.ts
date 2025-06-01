"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"

export interface CalendarTask {
  id: string
  title: string
  description: string
  date: string
  startTime: string
  endTime: string
  priority: "high" | "medium" | "low"
  completed: boolean
  type: "task" | "event"
  location?: string
  attendees?: number
}

interface CalendarStore {
  tasks: CalendarTask[]
  addTask: (task: Omit<CalendarTask, "id" | "completed">) => void
  addTasks: (tasks: Omit<CalendarTask, "id" | "completed">[]) => void
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

      addTasks: (tasks) => {
        const newTasks: CalendarTask[] = tasks.map((task, index) => ({
          ...task,
          id: `task-${Date.now()}-${index}-${Math.random().toString(36).substring(7)}`,
          completed: false,
        }))
        set((state) => ({
          tasks: [...state.tasks, ...newTasks],
        }))
      },

      toggleTask: (id) => {
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
