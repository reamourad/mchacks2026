import Link from "next/link"
import { Github, Instagram, Linkedin, Twitter } from "lucide-react"

export default function Footer() {
  const footerBgUrl = process.env.NEXT_PUBLIC_FOOTER_BG_URL || "/footer-bg.png"

  return (
    <footer
      className="relative overflow-hidden py-12"
      style={
        {
          backgroundImage: `url(${footerBgUrl})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
        }
      }
    >
      <div className="absolute inset-0 bg-[#151E23]/85" />

      <div className="relative mx-auto w-full max-w-7xl px-6 md:px-12">
        <div className="mb-10 flex flex-col items-center justify-between gap-4 md:flex-row">
          <div className="text-center text-sm text-foreground/70 md:text-left">
            Ready to start?
          </div>
          <Link
            href="/editor"
            className="inline-flex h-11 items-center justify-center rounded-xl bg-primary px-6 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Start creating
          </Link>
        </div>

        <div className="grid items-center gap-8 md:grid-cols-3">
          <div className="flex flex-col gap-2 text-sm text-foreground/60">
            <div className="text-foreground/70">About us</div>
            <a className="w-fit text-foreground/60 transition-colors hover:text-primary" href="#how-it-works">
              Product
            </a>
            <a className="w-fit text-foreground/60 transition-colors hover:text-primary" href="#contact">
              Contact us
            </a>
          </div>

          <div className="text-center text-sm text-foreground/60">© Copyright Xpresso 2026</div>

          <div className="flex items-center justify-start gap-3 md:justify-end">
            <a
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-foreground/10 bg-black/20 text-foreground/60 transition-colors hover:border-primary/30 hover:text-primary"
              href="#"
              aria-label="Twitter"
            >
              <Twitter className="h-4 w-4" />
            </a>
            <a
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-foreground/10 bg-black/20 text-foreground/60 transition-colors hover:border-primary/30 hover:text-primary"
              href="#"
              aria-label="Instagram"
            >
              <Instagram className="h-4 w-4" />
            </a>
            <a
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-foreground/10 bg-black/20 text-foreground/60 transition-colors hover:border-primary/30 hover:text-primary"
              href="#"
              aria-label="LinkedIn"
            >
              <Linkedin className="h-4 w-4" />
            </a>
            <a
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-foreground/10 bg-black/20 text-foreground/60 transition-colors hover:border-primary/30 hover:text-primary"
              href="#"
              aria-label="GitHub"
            >
              <Github className="h-4 w-4" />
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}
