"use client"

import Link from "next/link"
import Logo from "@/components/logo"
import { useUser } from '@auth0/nextjs-auth0/client'

export default function Navbar() {
  const { user, isLoading } = useUser()

  return (
    <nav className="sticky top-0 z-50 flex h-16 items-center justify-between border-b-0 bg-background/80 px-6 backdrop-blur-sm md:px-8">
      <Logo />

      <div className="flex items-center gap-4">
        {!isLoading && (
          <>
            {user ? (
              <>
                <div className="flex items-center gap-3">
                  {user.picture && (
                    <img
                      src={user.picture}
                      alt={user.name || 'User'}
                      className="h-8 w-8 rounded-full border-2 border-primary"
                    />
                  )}
                  <span className="text-sm text-foreground hidden md:inline">
                    {user.name || user.email}
                  </span>
                </div>

                <Link href="/editor">
                  <button
                    className="nav-button"
                    data-text="Start Creating"
                  >
                    <span>Start Creating</span>
                  </button>
                </Link>

                <a href="/auth/logout">
                  <button
                    className="nav-button"
                    data-text="Logout"
                  >
                    <span>Logout</span>
                  </button>
                </a>
              </>
            ) : (
              <>
                <button
                  className="nav-button"
                  data-text="Menu"
                >
                  <span>Menu</span>
                </button>

                <a href="/auth/login">
                  <button
                    className="nav-button"
                    data-text="Login"
                  >
                    <span>Login</span>
                  </button>
                </a>
              </>
            )}
          </>
        )}
      </div>
    </nav>
  )
}
