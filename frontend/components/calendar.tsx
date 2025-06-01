"use client"

import { useState } from "react"
import { CalendarIcon, Plus, Sparkles } from "lucide-react"
import { format } from "date-fns"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Calendar as CalendarComponent } from "@/components/ui/calendar"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { toast } from "@/components/ui/use-toast"
import { useCalendarStore } from "@/lib/calendar-store"

type CalendarViewType = "daily" | "weekly" | "monthly"

interface CalendarProps {
  view: CalendarViewType
}

export default function Calendar({ view }: CalendarProps) {
  const [date, setDate] = useState<Date>(new Date())
  const [isAddTaskOpen, setIsAddTaskOpen] = useState(false)
  const { tasks, addTask, toggleTask, deleteTask } = useCalendarStore()

  const addNewTask = (title: string, description: string, priority: "high" | "medium" | "low" = "medium") => {
    addTask({
      title,
      description,
      date: date.toISOString().split("T")[0],
      startTime: "09:00",
      endTime: "10:00",
      priority,
      type: "task",
    })
    setIsAddTaskOpen(false)

    toast({
      title: "Task Created",
      description: `"${title}" has been added to your calendar`,
    })
  }

  const handleToggleTask = (id: string) => {
    toggleTask(id)
  }

  const handleDeleteTask = (id: string) => {
    deleteTask(id)
    toast({
      title: "Task Deleted",
      description: "Task has been removed from your calendar",
    })
  }

  const getPriorityClass = (priority: "high" | "medium" | "low") => {
    switch (priority) {
      case "high":
        return "priority-high"
      case "medium":
        return "priority-medium"
      case "low":
        return "priority-low"
      default:
        return "priority-medium"
    }
  }

  const getPriorityBadgeVariant = (priority: "high" | "medium" | "low") => {
    switch (priority) {
      case "high":
        return "destructive"
      case "medium":
        return "default"
      case "low":
        return "secondary"
      default:
        return "default"
    }
  }

  // Get tasks for the selected date
  const getTasksForDate = (targetDate: Date) => {
    const dateString = targetDate.toISOString().split("T")[0]
    return tasks.filter((task) => task.date === dateString)
  }

  // Get tasks for a specific date string
  const getTasksForDateString = (dateString: string) => {
    return tasks.filter((task) => task.date === dateString)
  }

  return (
    <Card className="w-full mt-6 card-colorful card-hover shadow-lg">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <CardTitle className="text-2xl font-bold flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-purple-500 flex items-center justify-center">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          <span className="text-purple-600">
            {view === "daily" && "Daily Tasks"}
            {view === "weekly" && "Weekly Schedule"}
            {view === "monthly" && "Monthly Overview"}
          </span>
        </CardTitle>
        <div className="flex items-center space-x-3">
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant={"outline"}
                className={cn(
                  "justify-start text-left font-normal bg-white border-slate-200 hover:bg-purple-50 hover:border-purple-300 transition-all duration-200",
                  !date && "text-muted-foreground",
                )}
              >
                <CalendarIcon className="mr-2 h-4 w-4" />
                {date ? format(date, "PPP") : <span>Pick a date</span>}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0 card-colorful">
              <CalendarComponent
                mode="single"
                selected={date}
                onSelect={(date) => date && setDate(date)}
                initialFocus
              />
            </PopoverContent>
          </Popover>

          <Dialog open={isAddTaskOpen} onOpenChange={setIsAddTaskOpen}>
            <DialogTrigger asChild>
              <Button size="icon" className="btn-purple shadow-lg">
                <Plus className="h-4 w-4" />
              </Button>
            </DialogTrigger>
            <DialogContent className="card-colorful">
              <DialogHeader>
                <DialogTitle className="text-purple-600 text-xl">Add New Task</DialogTitle>
              </DialogHeader>
              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  const formData = new FormData(e.currentTarget)
                  const title = formData.get("title") as string
                  const description = formData.get("description") as string
                  const priority = formData.get("priority") as "high" | "medium" | "low"
                  if (title) addNewTask(title, description, priority)
                }}
                className="space-y-4 pt-4"
              >
                <div className="space-y-2">
                  <Input
                    name="title"
                    placeholder="Task title"
                    required
                    className="bg-white border-slate-200 focus:border-purple-300 focus:ring-purple-200"
                  />
                </div>
                <div className="space-y-2">
                  <Textarea
                    name="description"
                    placeholder="Description (optional)"
                    className="bg-white border-slate-200 focus:border-purple-300 focus:ring-purple-200"
                  />
                </div>
                <div className="space-y-2">
                  <select
                    name="priority"
                    className="w-full p-3 rounded-lg bg-white border border-slate-200 focus:border-purple-300 focus:ring-2 focus:ring-purple-200 transition-all duration-200"
                  >
                    <option value="medium">Medium Priority</option>
                    <option value="high">High Priority</option>
                    <option value="low">Low Priority</option>
                  </select>
                </div>
                <Button type="submit" className="w-full btn-purple shadow-lg">
                  Add Task
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </CardHeader>
      <CardContent>
        {view === "daily" && (
          <div className="space-y-4">
            {getTasksForDate(date).length > 0 ? (
              getTasksForDate(date).map((task) => (
                <div
                  key={task.id}
                  className={cn(
                    "flex items-start space-x-4 rounded-xl p-5 transition-all duration-300 hover:shadow-md border border-white/50",
                    getPriorityClass(task.priority),
                    task.completed ? "opacity-60" : "",
                  )}
                >
                  <Checkbox
                    checked={task.completed}
                    onCheckedChange={() => handleToggleTask(task.id)}
                    className="mt-1"
                  />
                  <div className="flex-1 space-y-3">
                    <div className="flex items-center justify-between">
                      <p
                        className={cn("font-semibold text-lg", task.completed && "line-through text-muted-foreground")}
                      >
                        {task.title}
                      </p>
                      <div className="flex items-center gap-2">
                        <Badge variant={getPriorityBadgeVariant(task.priority)} className="capitalize font-medium">
                          {task.priority}
                        </Badge>
                        <Badge variant="outline" className="bg-white/80">
                          {task.startTime} - {task.endTime}
                        </Badge>
                      </div>
                    </div>
                    {task.description && <p className="text-sm text-slate-600">{task.description}</p>}
                    <div className="flex gap-2 mt-3">
                      <Button
                        variant="outline"
                        size="sm"
                        className="bg-white hover:bg-purple-50 hover:border-purple-300 transition-all duration-200"
                      >
                        Edit
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-red-600 hover:bg-red-50 hover:border-red-300 transition-all duration-200"
                        onClick={() => handleDeleteTask(task.id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="flex h-[300px] items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-white">
                <div className="text-center">
                  <p className="text-sm text-slate-500 mb-3">No tasks for this day</p>
                  <Button
                    variant="outline"
                    className="bg-white hover:bg-purple-50 hover:border-purple-300"
                    onClick={() => setIsAddTaskOpen(true)}
                  >
                    Add Task
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {view === "weekly" && (
          <div className="grid grid-cols-7 gap-4">
            {Array.from({ length: 7 }).map((_, i) => {
              const dayDate = new Date(date.getTime())
              dayDate.setDate(date.getDate() - date.getDay() + i)
              const dayDateString = dayDate.toISOString().split("T")[0]
              const dayTasks = getTasksForDateString(dayDateString)

              return (
                <div key={i} className="min-h-[180px] rounded-xl border border-slate-200 p-4 card-colorful card-hover">
                  <div className="text-sm font-semibold mb-3 text-blue-600">{format(dayDate, "EEE d")}</div>
                  <div className="space-y-2">
                    {dayTasks.map((task) => (
                      <div
                        key={task.id}
                        className={cn(
                          "text-sm p-3 rounded-lg transition-all duration-200 border border-white/50",
                          getPriorityClass(task.priority),
                          task.completed ? "opacity-60 line-through" : "",
                        )}
                      >
                        <div className="font-medium">{task.title}</div>
                        <div className="text-xs text-slate-600 mt-1">
                          {task.startTime} - {task.endTime}
                        </div>
                        {task.description && (
                          <div className="text-xs text-slate-600 mt-1 truncate">{task.description}</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {view === "monthly" && (
          <div className="grid grid-cols-7 gap-2">
            {Array.from({ length: 42 }).map((_, i) => {
              const currentDate = new Date(date.getFullYear(), date.getMonth(), 1)
              const firstDay = currentDate.getDay()
              const day = i - firstDay + 1
              currentDate.setDate(day)

              const isCurrentMonth = currentDate.getMonth() === date.getMonth()
              const isToday = format(currentDate, "yyyy-MM-dd") === format(new Date(), "yyyy-MM-dd")

              const dayDateString = currentDate.toISOString().split("T")[0]
              const dayTasks = getTasksForDateString(dayDateString)

              return (
                <div
                  key={i}
                  className={cn(
                    "h-24 p-2 border rounded-lg overflow-hidden transition-all duration-200 card-hover",
                    !isCurrentMonth && "opacity-40 bg-slate-100/50",
                    isToday && "ring-2 ring-purple-400 bg-purple-50",
                    "card-colorful",
                  )}
                >
                  <div className={cn("text-sm font-medium mb-1", isToday && "text-purple-600 font-bold")}>
                    {format(currentDate, "d")}
                  </div>
                  <div className="space-y-1">
                    {dayTasks.slice(0, 2).map((task) => (
                      <div
                        key={task.id}
                        className={cn("text-xs p-1 rounded truncate", getPriorityClass(task.priority))}
                      >
                        {task.title}
                      </div>
                    ))}
                    {dayTasks.length > 2 && (
                      <div className="text-xs text-slate-500 font-medium">+{dayTasks.length - 2} more</div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
