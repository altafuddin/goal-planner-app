"use client"

import { createContext, useContext, useState, type ReactNode } from "react"

interface UserInfo {
  email: string
  name: string
  picture: string
}

interface AuthContextType {
  isAuthenticated: boolean
  userInfo: UserInfo | null
  isLoading: boolean
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  userInfo: null,
  isLoading: false,
  signOut: async () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const signOut = async () => {
    try {
      // Update state
      setUserInfo(null)
      setIsAuthenticated(false)
    } catch (error) {
      console.error("Error signing out:", error)
    }
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, userInfo, isLoading, signOut }}>{children}</AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
