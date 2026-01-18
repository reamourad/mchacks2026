"use client"

import { useState, useEffect } from "react"
import Link from "next/link"

export default function Hero() {
  const [showAnimation, setShowAnimation] = useState(true)
  const [animationText, setAnimationText] = useState("Xpresso")
  const [showHero, setShowHero] = useState(false)
  const [sloganFontFamily, setSloganFontFamily] = useState("var(--font-slogan), serif")
  const [sloganFontWeight, setSloganFontWeight] = useState<number>(400)

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
              setShowHero(true)
              setTimeout(() => {
                setShowAnimation(false)
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

  useEffect(() => {
    if (!showHero) return

    const fonts = [
      { family: "var(--font-playfair), serif", weight: 400 },
      { family: "var(--font-bowlby), system-ui", weight: 400 },
      { family: '"Playwrite NG Modern", cursive', weight: 300 },
      { family: "var(--font-cherry-bomb-one), system-ui", weight: 400 },
      { family: "var(--font-limelight), serif", weight: 400 },
      { family: "var(--font-monsieur-la-doulaise), cursive", weight: 400 },
    ]

    const loops = 3
    const stepMs = 1000
    const totalSteps = fonts.length * loops
    let step = 0

    setSloganFontFamily(fonts[0].family)
    setSloganFontWeight(fonts[0].weight)

    const interval = setInterval(() => {
      step++

      if (step >= totalSteps) {
        clearInterval(interval)
        setSloganFontFamily("var(--font-slogan), serif")
        setSloganFontWeight(500)
        return
      }

      const next = fonts[step % fonts.length]
      setSloganFontFamily(next.family)
      setSloganFontWeight(next.weight)
    }, stepMs)

    return () => {
      clearInterval(interval)
    }
  }, [showHero])

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
            <h1
              className="font-bold leading-none text-accent"
              style={{
                fontFamily: "var(--font-playfair), serif",
                fontSize: "clamp(4.5rem, 18vw, 18rem)",
                lineHeight: 0.85,
              }}
            >
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
            <h2
              className="text-4xl font-bold leading-tight md:text-5xl lg:text-6xl"
              style={{ fontFamily: sloganFontFamily, color: "#F1FAEE", fontWeight: sloganFontWeight }}
            >
              Make a video in the time it takes to make an{" "}
              <span className="text-accent">Xpresso</span>
            </h2>
          </div>

          {/* Right Side - 40% */}
          <div className="flex w-full items-center justify-center md:w-[40%]">
            <Link href="/editor">
              <button
                className="group relative flex h-[clamp(180px,15vw,360px)] w-[clamp(180px,15vw,360px)] items-center justify-center transition-all duration-300 hover:scale-110"
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
                    d="M32 24 Q32 20 36 22 L78 46 Q82 48 82 50 Q82 52 78 54 L36 78 Q32 80 32 76 Z"
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
