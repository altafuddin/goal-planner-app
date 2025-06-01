"use client";
import { CalendarClock, MapPin, Users, Sparkles } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { isToday, isTomorrow, isThisWeek, addDays, parseISO } from "date-fns"
import { useCalendarStore } from "@/lib/calendar-store"

export default function UpcomingEvents() {
  const { tasks } = useCalendarStore()

  // Convert calendar tasks to events format and filter for upcoming
  const upcomingTasks = tasks
    .filter((task) => {
      const taskDate = parseISO(task.date)
      return taskDate >= new Date() || isToday(taskDate)
    })
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

  // Group events by time period
  const todayEvents = upcomingTasks.filter((task) => isToday(parseISO(task.date)))
  const tomorrowEvents = upcomingTasks.filter((task) => isTomorrow(parseISO(task.date)))
  const thisWeekEvents = upcomingTasks.filter((task) => {
    const taskDate = parseISO(task.date)
    return isThisWeek(taskDate) && !isToday(taskDate) && !isTomorrow(taskDate)
  })
  const laterEvents = upcomingTasks.filter((task) => {
    const taskDate = parseISO(task.date)
    return !isThisWeek(taskDate) || taskDate > addDays(new Date(), 7)
  })

  // Function to get badge variant based on task type and priority
  const getBadgeVariant = (task: any) => {
    if (task.type === "event") {
      return "default"
    }
    switch (task.priority) {
      case "high":
        return "destructive"
      case "medium":
        return "default"
      case "low":
        return "secondary"
      default:
        return "outline"
    }
  }

  // Component to render a single event
  const EventCard = ({ task }: { task: any }) => (
    <Card className={`mb-3 card-colorful card-hover border border-slate-200 ${task.completed ? "opacity-60" : ""}`}>
      <CardContent className="p-4">
        <div className="flex justify-between items-start">
          <div>
            <h3 className={`font-semibold text-slate-800 ${task.completed ? "line-through" : ""}`}>{task.title}</h3>
            {task.description && <p className="text-xs text-slate-600 mt-1">{task.description}</p>}
          </div>
          <div className="flex gap-1">
            <Badge variant={getBadgeVariant(task)} className="font-medium capitalize">
              {task.type === "event" ? task.type : task.priority}
            </Badge>
            {task.completed && (
              <Badge variant="outline" className="text-green-600 border-green-600 text-xs">
                Done
              </Badge>
            )}
          </div>
        </div>

        <div className="mt-3 space-y-1">
          <div className="flex items-center text-xs text-slate-500">
            <CalendarClock className="h-3 w-3 mr-2" />
            <span>
              {task.startTime} - {task.endTime}
            </span>
          </div>

          {task.location && (
            <div className="flex items-center text-xs text-slate-500">
              <MapPin className="h-3 w-3 mr-2" />
              <span>{task.location}</span>
            </div>
          )}

          {task.attendees && (
            <div className="flex items-center text-xs text-slate-500">
              <Users className="h-3 w-3 mr-2" />
              <span>{task.attendees} attendees</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )

  // Component to render a time period section
  const TimeSection = ({ title, events, color }: { title: string; events: any[]; color: string }) =>
    events.length > 0 ? (
      <div className="mb-6">
        <h2 className="text-sm font-bold text-slate-700 mb-3 flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${color}`}></div>
          {title} ({events.length})
        </h2>
        <div>
          {events.map((task) => (
            <EventCard key={task.id} task={task} />
          ))}
        </div>
      </div>
    ) : null

  return (
    <Card className="mt-6 card-colorful card-hover shadow-lg">
      <CardHeader className="px-4 py-4 border-b border-slate-200">
        <CardTitle className="text-lg font-bold flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-orange-500 flex items-center justify-center">
            <Sparkles className="h-4 w-4 text-white" />
          </div>
          <span className="text-orange-600">Upcoming Events</span>
        </CardTitle>
      </CardHeader>
      <ScrollArea className="h-[350px]">
        <CardContent className="p-4">
          <TimeSection title="Today" events={todayEvents} color="bg-red-500" />
          <TimeSection title="Tomorrow" events={tomorrowEvents} color="bg-orange-500" />
          <TimeSection title="This Week" events={thisWeekEvents} color="bg-blue-500" />
          <TimeSection title="Later" events={laterEvents} color="bg-green-500" />

          {upcomingTasks.length === 0 && (
            <div className="flex h-[200px] items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-white">
              <p className="text-sm text-slate-500">No upcoming events</p>
            </div>
          )}
        </CardContent>
      </ScrollArea>
    </Card>
  )
}
