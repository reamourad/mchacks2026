import type { Metadata } from "next"
import {
  Bowlby_One_SC,
  Cherry_Bomb_One,
  Cormorant_Garamond,
  Inter,
  Limelight,
  Monsieur_La_Doulaise,
  Playfair_Display,
} from "next/font/google"
import "./globals.css"
import Navbar from "@/components/navbar"
import { Providers } from "@/components/providers"

const inter = Inter({ subsets: ["latin"] })
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
<<<<<<< HEAD
      <body
        className={`${inter.className} ${playfair.variable} ${sloganFont.variable} ${bowlby.variable} ${cherryBombOne.variable} ${limelight.variable} ${monsieurLaDoulaise.variable}`}
      >
        <Navbar />
        {children}
=======
      <body className={`${inter.className} ${playfair.variable}`}>
        <Providers>
          <Navbar />
          {children}
        </Providers>
>>>>>>> ac64935ffdba84152be2d01871bd5a329fe070bf
      </body>
    </html>
  )
}
