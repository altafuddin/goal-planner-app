"use client"

import { Settings, Calendar, MessageSquare } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import Link from "next/link"
import GoogleAuthButton from "@/components/google-auth-button"
import { useAuth } from "@/lib/auth-context"

export default function TopNavigation() {
  const { isAuthenticated, userInfo, signOut } = useAuth()

  return (
    <div className="h-16 border-b border-slate-200 flex items-center justify-between px-6 bg-white shadow-sm">
      <div className="flex items-center">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-purple-500 flex items-center justify-center">
            <span className="text-white font-bold text-sm">T</span>
          </div>
          <h1 className="text-2xl font-bold text-purple-600">TaskFlow</h1>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        <GoogleAuthButton />

        <Link href="/calendar">
          <Button variant="ghost" size="icon" className="hover:bg-purple-100 hover:text-purple-600">
            <Calendar className="h-5 w-5" />
          </Button>
        </Link>

        <Link href="/events">
          <Button variant="ghost" size="icon" className="hover:bg-blue-100 hover:text-blue-600">
            <MessageSquare className="h-5 w-5" />
          </Button>
        </Link>

        <Link href="/settings">
          <Button variant="ghost" size="icon" className="hover:bg-orange-100 hover:text-orange-600">
            <Settings className="h-5 w-5" />
          </Button>
        </Link>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-10 w-10 rounded-full hover:ring-2 hover:ring-purple-200">
              <Avatar className="h-10 w-10">
                <AvatarImage src="/placeholder.svg?height=40&width=40" alt="User" />
                <AvatarFallback className="bg-teal-500 text-white font-semibold">U</AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56 card-colorful" align="end" forceMount>
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">User</p>
                <p className="text-xs leading-none text-muted-foreground">user@example.com</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <Link href="/profile">
              <DropdownMenuItem className="hover:bg-purple-50">Profile</DropdownMenuItem>
            </Link>
            <Link href="/settings">
              <DropdownMenuItem className="hover:bg-blue-50">Settings</DropdownMenuItem>
            </Link>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => signOut()} className="hover:bg-red-50 text-red-600">
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
}
