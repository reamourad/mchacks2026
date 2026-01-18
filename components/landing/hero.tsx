"use client"

import { useState, useEffect } from "react"
import Link from "next/link"

export default function Hero() {
  const [showAnimation, setShowAnimation] = useState(true)
  const [animationText, setAnimationText] = useState("Xpresso")
  const [showHero, setShowHero] = useState(false)

  useEffect(() => {
    const sequence = [
      { text: "Xpresso", delay: 200 },
      { text: "Xpress o", delay: 100 },
      { text: "Xpress v o", delay: 100 },
      { text: "Xpress vi o", delay: 100 },
      { text: "Xpress vid o", delay: 100 },
      { text: "Xpress video", delay: 300 },
    ]

    let currentIndex = 0
    const timers: NodeJS.Timeout[] = []

    const updateText = () => {
      if (currentIndex < sequence.length) {
        setAnimationText(sequence[currentIndex].text)
        const timer = setTimeout(() => {
          currentIndex++
          if (currentIndex < sequence.length) {
            updateText()
          } else {
            // Wait for animation to complete (~2s), then fade out and transition
            setTimeout(() => {
              setShowAnimation(false)
              setTimeout(() => {
                setShowHero(true)
              }, 300)
            }, 500)
          }
        }, sequence[currentIndex].delay)
        timers.push(timer)
      }
    }

    updateText()

    return () => {
      timers.forEach(timer => clearTimeout(timer))
    }
  }, [])

  return (
    <>
      {/* Animation Section */}
      {showAnimation && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-background">
          <div
            className="mb-8 text-center"
            style={{
              animation: "growAndFade 2000ms ease-out forwards",
            }}
          >
            <h1 className="text-6xl font-bold text-accent md:text-8xl lg:text-9xl">
              {animationText}
            </h1>
          </div>
        </div>
      )}

      {/* Hero Section */}
      {showHero && (
        <section className="flex min-h-screen flex-col items-center justify-center gap-12 py-20 md:flex-row md:py-32">
          {/* Left Side - 60% */}
          <div className="w-full md:w-[60%]">
            <h2 className="text-4xl font-bold leading-tight md:text-5xl lg:text-6xl" style={{ fontFamily: 'var(--font-playfair), serif', color: '#F1FAEE' }}>
              Make a video in the time it takes to make an{" "}
              <span className="text-accent">Xpresso</span>
            </h2>
          </div>

          {/* Right Side - 40% */}
          <div className="flex w-full items-center justify-center md:w-[40%]">
            <Link href="/editor">
              <button
                className="group relative flex h-32 w-32 items-center justify-center transition-all duration-300 hover:scale-110 md:h-40 md:w-40"
                aria-label="Play video"
              >
                {/* Triangle Play Button - Blue background by default, fills with banana cream on hover */}
                <svg
                  className="play-triangle transition-all duration-500"
                  width="100%"
                  height="100%"
                  viewBox="0 0 100 100"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M15 15 L15 85 L80 50 Z"
                    fill="#A8DADC"
                    className="transition-all duration-500 group-hover:fill-[#FFE95B]"
                  />
                </svg>
              </button>
            </Link>
          </div>
        </section>
      )}
    </>
  )
}
