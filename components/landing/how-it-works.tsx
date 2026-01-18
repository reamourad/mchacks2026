import { Layers, Mic, Scan, Subtitles } from "lucide-react"

export default function HowItWorks() {
  const demoVideoSrc = process.env.NEXT_PUBLIC_DEMO_VIDEO_URL

  return (
    <section id="how-it-works" className="py-12">
      <h2 className="mb-14 text-center text-4xl font-semibold text-foreground md:text-5xl" style={{ fontFamily: "var(--font-slogan)" }}>
        See Xpresso in Action
      </h2>

      <div className="relative mx-auto grid w-full max-w-6xl items-center gap-10 md:grid-cols-3 md:gap-12">
        <div className="relative z-10 flex flex-col gap-20">
          <div className="w-full rounded-xl border border-secondary/70 bg-secondary/15 px-5 py-5 backdrop-blur-sm">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-secondary/70 bg-secondary/10">
                <Scan className="h-5 w-5 text-secondary" />
              </div>
              <div className="text-lg font-semibold text-foreground">Video recognition</div>
            </div>
          </div>
          <div className="w-full rounded-xl border border-secondary/70 bg-secondary/15 px-5 py-5 backdrop-blur-sm">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-secondary/70 bg-secondary/10">
                <Layers className="h-5 w-5 text-secondary" />
              </div>
              <div className="text-lg font-semibold text-foreground">Section generator</div>
            </div>
          </div>
        </div>

        <div className="relative z-10 mx-auto w-full max-w-[340px]">
          <div className="relative overflow-hidden rounded-[2.25rem] border border-foreground/25 bg-background/40 p-3 shadow-[0_0_0_1px_rgba(241,250,238,0.08)] backdrop-blur-sm">
            <div className="overflow-hidden rounded-[1.75rem] bg-black">
              <div className="aspect-[9/16] w-full">
                {demoVideoSrc ? (
                  <video
                    className="h-full w-full object-cover"
                    src={demoVideoSrc}
                    controls
                    playsInline
                  />
                ) : (
                  <div className="flex h-full w-full items-center justify-center bg-black/60 px-6 text-center text-sm text-foreground/80">
                    Add a demo video and set NEXT_PUBLIC_DEMO_VIDEO_URL
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="relative z-10 flex flex-col gap-20">
          <div className="w-full rounded-xl border border-secondary/70 bg-secondary/15 px-5 py-5 backdrop-blur-sm">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-secondary/70 bg-secondary/10">
                <Mic className="h-5 w-5 text-secondary" />
              </div>
              <div className="text-lg font-semibold text-foreground">Voice over recognition</div>
            </div>
          </div>
          <div className="w-full rounded-xl border border-secondary/70 bg-secondary/15 px-5 py-5 backdrop-blur-sm">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-secondary/70 bg-secondary/10">
                <Layers className="h-5 w-5 text-secondary" />
              </div>
              <div className="text-lg font-semibold text-foreground">Cool fonts</div>
            </div>
          </div>
          <div className="w-full rounded-xl border border-secondary/70 bg-secondary/15 px-5 py-5 backdrop-blur-sm">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-secondary/70 bg-secondary/10">
                <Subtitles className="h-5 w-5 text-secondary" />
              </div>
              <div className="text-lg font-semibold text-foreground">Captions</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
