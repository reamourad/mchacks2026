"use client"

import Link from "next/link"
import Logo from "@/components/logo"

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-50 flex h-16 items-center justify-between border-b-0 bg-background/80 px-6 backdrop-blur-sm md:px-8">
      <Logo />
      
      <div className="flex items-center gap-4">
        <button
          className="nav-button"
          data-text="Menu"
        >
          <span>Menu</span>
        </button>
        
        <Link href="/editor">
          <button
            className="nav-button"
            data-text="Start Creating"
          >
            <span>Start Creating</span>
          </button>
        </Link>
      </div>
    </nav>
  )
}
