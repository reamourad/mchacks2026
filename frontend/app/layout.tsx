import type { Metadata } from "next"
import {
  Bowlby_One_SC,
  Cherry_Bomb_One,
  Cormorant_Garamond,
  Limelight,
  Monsieur_La_Doulaise,
  Playfair_Display,
  Quicksand,
} from "next/font/google"
import "./globals.css"
import Navbar from "@/components/navbar"
import { Providers } from "@/components/providers"

const quicksand = Quicksand({ subsets: ["latin"], display: "swap" })
const playfair = Playfair_Display({ 
  subsets: ["latin"],
  variable: "--font-playfair",
  display: "swap",
})

const sloganFont = Cormorant_Garamond({
  subsets: ["latin"],
  variable: "--font-slogan",
  weight: ["300", "400", "500", "600"],
  display: "swap",
})

const bowlby = Bowlby_One_SC({
  subsets: ["latin"],
  variable: "--font-bowlby",
  weight: "400",
  display: "swap",
})

const cherryBombOne = Cherry_Bomb_One({
  subsets: ["latin"],
  variable: "--font-cherry-bomb-one",
  weight: "400",
  display: "swap",
})

const limelight = Limelight({
  subsets: ["latin"],
  variable: "--font-limelight",
  weight: "400",
  display: "swap",
})

const monsieurLaDoulaise = Monsieur_La_Doulaise({
  subsets: ["latin"],
  variable: "--font-monsieur-la-doulaise",
  weight: "400",
  display: "swap",
})

export const metadata: Metadata = {
  title: "mchacks2026",
  description: "mchacks2026 application",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Playwrite+NG+Modern:wght@300;400;500;600;700&display=swap"
        />
      </head>
      <body
        className={`${quicksand.className} ${playfair.variable} ${sloganFont.variable} ${bowlby.variable} ${cherryBombOne.variable} ${limelight.variable} ${monsieurLaDoulaise.variable}`}
      >
        <Providers>
          <Navbar />
          {children}
        </Providers>
      </body>
    </html>
  )
}
