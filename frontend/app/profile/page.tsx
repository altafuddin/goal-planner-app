"use client"

import type React from "react"

import { useState } from "react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import Link from "next/link"
import { ArrowLeft, Mail, Phone, MapPin, Briefcase, Calendar, Edit, Save } from "lucide-react"
import { toast } from "@/components/ui/use-toast"

export default function ProfilePage() {
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [profileData, setProfileData] = useState({
    firstName: "John",
    lastName: "Doe",
    email: "john.doe@example.com",
    phone: "+1 (555) 123-4567",
    location: "San Francisco, CA",
    company: "Acme Inc.",
    position: "Product Manager",
  })

  const handleSaveProfile = (formData: FormData) => {
    const updatedData = {
      firstName: formData.get("firstName") as string,
      lastName: formData.get("lastName") as string,
      email: formData.get("email") as string,
      phone: formData.get("phone") as string,
      location: formData.get("location") as string,
      company: formData.get("company") as string,
      position: formData.get("position") as string,
    }

    setProfileData(updatedData)
    setIsEditDialogOpen(false)

    toast({
      title: "Profile Updated",
      description: "Your profile information has been saved successfully.",
    })
  }

  return (
    <div className="flex flex-col min-h-screen bg-slate-50">
      <div className="border-b border-slate-200 bg-white">
        <div className="flex h-16 items-center px-6">
          <Link href="/" className="flex items-center text-sm font-medium hover:text-purple-600">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Link>
          <div className="ml-auto flex items-center space-x-2">
            <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" size="sm" className="hover:bg-purple-50 hover:border-purple-300">
                  <Edit className="mr-2 h-4 w-4" />
                  Edit Profile
                </Button>
              </DialogTrigger>
              <DialogContent className="card-colorful max-w-md">
                <DialogHeader>
                  <DialogTitle className="text-purple-600">Edit Profile</DialogTitle>
                </DialogHeader>
                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    const formData = new FormData(e.currentTarget)
                    handleSaveProfile(formData)
                  }}
                  className="space-y-4 pt-4"
                >
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="firstName">First Name</Label>
                      <Input id="firstName" name="firstName" defaultValue={profileData.firstName} />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="lastName">Last Name</Label>
                      <Input id="lastName" name="lastName" defaultValue={profileData.lastName} />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input id="email" name="email" type="email" defaultValue={profileData.email} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone">Phone</Label>
                    <Input id="phone" name="phone" defaultValue={profileData.phone} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="location">Location</Label>
                    <Input id="location" name="location" defaultValue={profileData.location} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="company">Company</Label>
                    <Input id="company" name="company" defaultValue={profileData.company} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="position">Position</Label>
                    <Input id="position" name="position" defaultValue={profileData.position} />
                  </div>
                  <div className="flex gap-2 pt-4">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setIsEditDialogOpen(false)}
                      className="flex-1"
                    >
                      Cancel
                    </Button>
                    <Button type="submit" className="btn-purple flex-1">
                      <Save className="mr-2 h-4 w-4" />
                      Save
                    </Button>
                  </div>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </div>

      <div className="flex-1 space-y-6 p-6">
        <div className="flex flex-col items-center space-y-4 sm:flex-row sm:space-y-0 sm:space-x-6">
          <Avatar className="h-24 w-24 shadow-lg">
            <AvatarImage src="/placeholder.svg?height=96&width=96" alt="User" />
            <AvatarFallback className="bg-purple-500 text-white text-2xl font-bold">
              {profileData.firstName.charAt(0)}
              {profileData.lastName.charAt(0)}
            </AvatarFallback>
          </Avatar>
          <div className="space-y-1 text-center sm:text-left">
            <h1 className="text-2xl font-bold text-purple-600">
              {profileData.firstName} {profileData.lastName}
            </h1>
            <p className="text-muted-foreground">{profileData.position}</p>
            <div className="flex flex-wrap justify-center gap-2 sm:justify-start">
              <Badge variant="outline" className="bg-blue-50 border-blue-200">
                <Mail className="mr-1 h-3 w-3" />
                {profileData.email}
              </Badge>
              <Badge variant="outline" className="bg-green-50 border-green-200">
                <Phone className="mr-1 h-3 w-3" />
                {profileData.phone}
              </Badge>
              <Badge variant="outline" className="bg-orange-50 border-orange-200">
                <MapPin className="mr-1 h-3 w-3" />
                {profileData.location}
              </Badge>
            </div>
          </div>
        </div>

        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="grid w-full max-w-md grid-cols-3 bg-slate-100">
            <TabsTrigger value="overview" className="data-[state=active]:bg-purple-500 data-[state=active]:text-white">
              Overview
            </TabsTrigger>
            <TabsTrigger value="activity" className="data-[state=active]:bg-blue-500 data-[state=active]:text-white">
              Activity
            </TabsTrigger>
            <TabsTrigger value="tasks" className="data-[state=active]:bg-green-500 data-[state=active]:text-white">
              Tasks
            </TabsTrigger>
          </TabsList>
          <TabsContent value="overview">
            <div className="grid gap-6 md:grid-cols-2">
              <Card className="card-colorful card-hover">
                <CardHeader>
                  <CardTitle className="text-purple-600">Personal Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-[20px_1fr] items-start gap-2">
                    <Briefcase className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium">Work</p>
                      <p className="text-sm text-muted-foreground">
                        {profileData.position} at {profileData.company}
                      </p>
                    </div>
                  </div>
                  <div className="grid grid-cols-[20px_1fr] items-start gap-2">
                    <Calendar className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <p className="font-medium">Joined</p>
                      <p className="text-sm text-muted-foreground">January 2022</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Card className="card-colorful card-hover">
                <CardHeader>
                  <CardTitle className="text-blue-600">Account Statistics</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Total Tasks</p>
                      <p className="text-2xl font-bold text-purple-600">248</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Completed</p>
                      <p className="text-2xl font-bold text-green-600">187</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Upcoming Events</p>
                      <p className="text-2xl font-bold text-blue-600">12</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Productivity</p>
                      <p className="text-2xl font-bold text-orange-600">75%</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
          <TabsContent value="activity">
            <Card className="card-colorful">
              <CardHeader>
                <CardTitle className="text-blue-600">Recent Activity</CardTitle>
                <CardDescription>Your activity from the past 30 days</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="flex items-start gap-4 border-b pb-4 last:border-0">
                      <div className={`rounded-full p-2 ${i % 2 === 0 ? "bg-green-100" : "bg-purple-100"}`}>
                        <Calendar className={`h-4 w-4 ${i % 2 === 0 ? "text-green-600" : "text-purple-600"}`} />
                      </div>
                      <div className="space-y-1">
                        <p className="text-sm font-medium">{i % 2 === 0 ? "Created a new task" : "Completed a task"}</p>
                        <p className="text-xs text-muted-foreground">
                          {i % 2 === 0 ? "Project planning for Q3" : "Review design mockups"}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {new Date(Date.now() - i * 86400000).toLocaleDateString()} at{" "}
                          {new Date(Date.now() - i * 86400000).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          <TabsContent value="tasks">
            <Card className="card-colorful">
              <CardHeader>
                <CardTitle className="text-green-600">Your Tasks</CardTitle>
                <CardDescription>Manage your tasks and track progress</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="flex items-center gap-4 border-b pb-4 last:border-0">
                      <input type="checkbox" className="h-4 w-4 rounded border-gray-300" defaultChecked={i % 3 === 0} />
                      <div className="space-y-1">
                        <p className={`text-sm font-medium ${i % 3 === 0 ? "line-through opacity-70" : ""}`}>
                          {
                            [
                              "Complete project proposal",
                              "Review design mockups",
                              "Team meeting",
                              "Client presentation",
                              "Update documentation",
                            ][(i - 1) % 5]
                          }
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Due {new Date(Date.now() + i * 86400000).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
              <CardFooter>
                <Button variant="outline" size="sm" className="w-full hover:bg-green-50 hover:border-green-300">
                  View All Tasks
                </Button>
              </CardFooter>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

function Badge({ variant, children, className }: { variant?: string; children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 ${
        variant === "outline" ? "border-input bg-background hover:bg-accent hover:text-accent-foreground" : ""
      } ${className || ""}`}
    >
      {children}
    </div>
  )
}
