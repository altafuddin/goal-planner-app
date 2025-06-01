"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { CalendarIcon, Clock, MapPin, Users, ArrowLeft, Plus, Check, Trash2, Info, MoreHorizontal } from "lucide-react"
import Link from "next/link"
import { format, addDays, isToday, isTomorrow, parseISO } from "date-fns"
import { useCalendarStore } from "@/lib/calendar-store"
import { toast } from "@/components/ui/use-toast"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"

export default function CalendarPage() {
  const { tasks, addTask, toggleTask, deleteTask } = useCalendarStore()
  const [selectedEvent, setSelectedEvent] = useState<any | null>(null)
  const [showEventDialog, setShowEventDialog] = useState(false)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [hoveredEvent, setHoveredEvent] = useState<string | null>(null)

  // Convert tasks to events format for display
  const events = tasks.map((task) => ({
    ...task,
    date: parseISO(task.date),
    type: task.type === "event" ? "meeting" : task.priority === "high" ? "deadline" : "reminder",
  }))

  // Get events for a specific date
  const getEventsForDate = (date: Date) => {
    const dateString = format(date, "yyyy-MM-dd")
    return events.filter((event) => format(event.date, "yyyy-MM-dd") === dateString)
  }

  // Get badge variant based on event type
  const getBadgeVariant = (type: string) => {
    switch (type) {
      case "meeting":
        return "default"
      case "deadline":
        return "destructive"
      case "reminder":
        return "secondary"
      case "personal":
        return "outline"
      default:
        return "default"
    }
  }

  // Get priority color
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "high":
        return "border-l-red-500"
      case "medium":
        return "border-l-yellow-500"
      case "low":
        return "border-l-green-500"
      default:
        return "border-l-gray-300"
    }
  }

  // Handle event actions
  const handleMarkDone = (eventId: string) => {
    toggleTask(eventId)
  }

  const handleDeleteEvent = (eventId: string) => {
    deleteTask(eventId)
    toast({
      title: "Event Deleted",
      description: "Event has been removed from your calendar",
    })
  }

  const handleShowDetails = (event: any) => {
    setSelectedEvent(event)
    setShowEventDialog(true)
  }

  const handleCreateEvent = (formData: FormData) => {
    const title = formData.get("title") as string
    const description = formData.get("description") as string
    const date = formData.get("date") as string
    const startTime = formData.get("startTime") as string
    const endTime = formData.get("endTime") as string
    const priority = formData.get("priority") as "high" | "medium" | "low"

    if (!title || !date || !startTime || !endTime) {
      toast({
        title: "Error",
        description: "Please fill in all required fields",
        variant: "destructive",
      })
      return
    }

    addTask({
      title,
      description,
      date,
      startTime,
      endTime,
      priority,
      type: "event",
    })

    setShowCreateDialog(false)
    toast({
      title: "Event Created",
      description: `"${title}" has been added to your calendar`,
    })
  }

  // Format date display
  const formatDateDisplay = (date: Date) => {
    if (isToday(date)) {
      return "Today"
    } else if (isTomorrow(date)) {
      return "Tomorrow"
    } else {
      return format(date, "EEE")
    }
  }

  return (
    <div className="flex flex-col min-h-screen bg-background">
      {/* Header */}
      <div className="border-b">
        <div className="flex h-14 items-center px-4">
          <Link href="/" className="flex items-center text-sm font-medium">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Link>
          <div className="ml-auto flex items-center space-x-2">
            <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
              <Button size="sm" onClick={() => setShowCreateDialog(true)}>
                <Plus className="mr-2 h-4 w-4" />
                New Event
              </Button>
              <DialogContent className="card-colorful">
                <DialogHeader>
                  <DialogTitle className="text-purple-600">Create New Event</DialogTitle>
                </DialogHeader>
                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    const formData = new FormData(e.currentTarget)
                    handleCreateEvent(formData)
                  }}
                  className="space-y-4 pt-4"
                >
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Title *</label>
                    <Input name="title" placeholder="Event title" required />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Description</label>
                    <Textarea name="description" placeholder="Event description" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Date *</label>
                    <Input name="date" type="date" required />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Start Time *</label>
                      <Input name="startTime" type="time" required />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">End Time *</label>
                      <Input name="endTime" type="time" required />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Priority</label>
                    <select
                      name="priority"
                      className="w-full p-2 rounded-md border border-slate-200 focus:border-purple-300 focus:ring-purple-200"
                    >
                      <option value="medium">Medium Priority</option>
                      <option value="high">High Priority</option>
                      <option value="low">Low Priority</option>
                    </select>
                  </div>
                  <div className="flex gap-2 pt-4">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setShowCreateDialog(false)}
                      className="flex-1"
                    >
                      Cancel
                    </Button>
                    <Button type="submit" className="btn-purple flex-1">
                      Create Event
                    </Button>
                  </div>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold">Calendar</h1>
          <p className="text-muted-foreground">View your events for the next 14 days</p>
        </div>

        {/* Calendar Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-7 gap-4">
          {Array.from({ length: 14 }, (_, i) => {
            const date = addDays(new Date(), i)
            const dayEvents = getEventsForDate(date)
            const isCurrentDay = isToday(date)

            return (
              <Card key={i} className={`h-fit ${isCurrentDay ? "ring-2 ring-primary" : ""}`}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center justify-between">
                    <div>
                      <div className={`font-medium ${isCurrentDay ? "text-primary" : ""}`}>
                        {formatDateDisplay(date)}
                      </div>
                      <div className="text-xs text-muted-foreground font-normal">{format(date, "MMM d")}</div>
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {dayEvents.length}
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="space-y-2">
                    {dayEvents.length > 0 ? (
                      dayEvents.map((event) => (
                        <div key={event.id} className="relative group">
                          <div
                            className={`p-2 rounded-md border-l-4 transition-all duration-200 ${getPriorityColor(event.priority)} ${
                              event.completed
                                ? "opacity-50 bg-muted/30 line-through"
                                : "hover:bg-muted/50 cursor-pointer"
                            }`}
                            onMouseEnter={() => setHoveredEvent(event.id)}
                            onMouseLeave={() => setHoveredEvent(null)}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1 min-w-0">
                                <p className={`text-sm font-medium truncate ${event.completed ? "line-through" : ""}`}>
                                  {event.title}
                                </p>
                                <p className="text-xs text-muted-foreground">
                                  {event.startTime} - {event.endTime}
                                </p>
                                {event.location && (
                                  <p className="text-xs text-muted-foreground truncate mt-1">📍 {event.location}</p>
                                )}
                              </div>
                              <div className="flex items-center gap-1">
                                {event.completed && <Check className="h-3 w-3 text-green-600" />}
                                <Badge variant={getBadgeVariant(event.type)} className="text-xs ml-2 flex-shrink-0">
                                  {event.type}
                                </Badge>
                              </div>
                            </div>

                            {/* Action Popover */}
                            {hoveredEvent === event.id && (
                              <div className="absolute top-1 right-1 z-10">
                                <Popover>
                                  <PopoverTrigger asChild>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="h-6 w-6 p-0 bg-background/80 backdrop-blur-sm border shadow-sm hover:bg-background"
                                    >
                                      <MoreHorizontal className="h-3 w-3" />
                                    </Button>
                                  </PopoverTrigger>
                                  <PopoverContent className="w-32 p-1" align="end">
                                    <div className="space-y-1">
                                      {!event.completed ? (
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          className="w-full justify-start h-8 px-2"
                                          onClick={(e) => {
                                            e.stopPropagation()
                                            handleMarkDone(event.id)
                                          }}
                                        >
                                          <Check className="h-3 w-3 mr-2" />
                                          Done
                                        </Button>
                                      ) : (
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          className="w-full justify-start h-8 px-2"
                                          onClick={(e) => {
                                            e.stopPropagation()
                                            handleMarkDone(event.id)
                                          }}
                                        >
                                          <Check className="h-3 w-3 mr-2" />
                                          Undone
                                        </Button>
                                      )}
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        className="w-full justify-start h-8 px-2"
                                        onClick={(e) => {
                                          e.stopPropagation()
                                          handleShowDetails(event)
                                        }}
                                      >
                                        <Info className="h-3 w-3 mr-2" />
                                        Details
                                      </Button>
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        className="w-full justify-start h-8 px-2 text-destructive hover:text-destructive"
                                        onClick={(e) => {
                                          e.stopPropagation()
                                          handleDeleteEvent(event.id)
                                        }}
                                      >
                                        <Trash2 className="h-3 w-3 mr-2" />
                                        Delete
                                      </Button>
                                    </div>
                                  </PopoverContent>
                                </Popover>
                              </div>
                            )}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-center py-4">
                        <p className="text-sm text-muted-foreground">No events</p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>

      {/* Event Detail Dialog */}
      <Dialog open={showEventDialog} onOpenChange={setShowEventDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CalendarIcon className="h-5 w-5" />
              Event Details
            </DialogTitle>
          </DialogHeader>

          {selectedEvent && (
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold text-lg flex items-center gap-2">
                  {selectedEvent.title}
                  {selectedEvent.completed && <Check className="h-4 w-4 text-green-600" />}
                </h3>
                <p className="text-sm text-muted-foreground mt-1">{selectedEvent.description}</p>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <CalendarIcon className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">{format(selectedEvent.date, "EEEE, MMMM d, yyyy")}</span>
                </div>

                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">
                    {selectedEvent.startTime} - {selectedEvent.endTime}
                  </span>
                </div>

                {selectedEvent.location && (
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">{selectedEvent.location}</span>
                  </div>
                )}

                {selectedEvent.attendees && (
                  <div className="flex items-center gap-2">
                    <Users className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">{selectedEvent.attendees} attendees</span>
                  </div>
                )}

                <div className="flex items-center gap-2">
                  <div className="h-4 w-4 flex items-center justify-center">
                    <div
                      className={`h-2 w-2 rounded-full ${
                        selectedEvent.priority === "high"
                          ? "bg-red-500"
                          : selectedEvent.priority === "medium"
                            ? "bg-yellow-500"
                            : "bg-green-500"
                      }`}
                    />
                  </div>
                  <span className="text-sm capitalize">{selectedEvent.priority} priority</span>
                </div>

                <div className="flex items-center gap-2">
                  <Badge variant={getBadgeVariant(selectedEvent.type)} className="capitalize">
                    {selectedEvent.type}
                  </Badge>
                  {selectedEvent.completed && (
                    <Badge variant="outline" className="text-green-600 border-green-600">
                      Completed
                    </Badge>
                  )}
                </div>
              </div>

              <div className="flex gap-2 pt-4">
                {!selectedEvent.completed ? (
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => {
                      handleMarkDone(selectedEvent.id)
                      setShowEventDialog(false)
                    }}
                  >
                    <Check className="h-3 w-3 mr-1" />
                    Mark Done
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => {
                      handleMarkDone(selectedEvent.id)
                      setShowEventDialog(false)
                    }}
                  >
                    Mark Undone
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1 text-destructive hover:text-destructive"
                  onClick={() => {
                    handleDeleteEvent(selectedEvent.id)
                    setShowEventDialog(false)
                  }}
                >
                  <Trash2 className="h-3 w-3 mr-1" />
                  Delete
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
