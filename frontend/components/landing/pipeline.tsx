import { Upload, SplitSquareVertical, Scan, Sparkles } from "lucide-react"

export default function Pipeline() {
  const steps = [
    {
      number: 1,
      title: "Input: clips, voiceover",
      description: "Upload raw footage and optional voiceover—Xpresso takes it from there.",
      Icon: Upload,
    },
    {
      number: 2,
      title: "Separate voiceover",
      description: "We isolate voiceover and audio layers to prep a clean edit pipeline.",
      Icon: SplitSquareVertical,
    },
    {
      number: 3,
      title: "Video sectioning",
      description: "AI scans your video to find scenes, moments, and natural cut points.",
      Icon: Scan,
    },
    {
      number: 4,
      title: "Add fonts, captions, etc",
      description: "Style your final video with fonts, captions, and on-brand polish.",
      Icon: Sparkles,
    },
  ]

  return (
    <section className="py-12">
      <h2 className="mb-20 text-center text-4xl font-semibold text-foreground md:text-5xl" style={{ fontFamily: "var(--font-slogan)" }}>
        From Raw Clips to Polished Content in 4 Steps
      </h2>

      <div className="relative mx-auto w-full max-w-6xl">
        <div className="grid gap-6 md:grid-cols-4 md:gap-8">
          {steps.map((step, index) => {
            const isUp = index % 2 === 0
            const Icon = step.Icon

            return (
              <div
                key={step.number}
                className={`relative rounded-xl border border-primary/30 bg-background/40 px-5 py-5 backdrop-blur-sm shadow-[0_0_0_1px_rgba(241,250,238,0.06)] ${
                  isUp ? "md:-translate-y-6" : "md:translate-y-6"
                }`}
              >
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full border border-primary/40 bg-primary/10 text-xs font-semibold text-primary">
                    {step.number}
                  </div>
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-primary/30 bg-black/25">
                    <Icon className="h-5 w-5 text-primary" />
                  </div>
                </div>

                <div className="text-lg font-semibold text-foreground">{step.title}</div>
                <div className="mt-2 text-sm text-foreground/70">{step.description}</div>
              </div>
            )
          })}
        </div>

        <div className="pointer-events-none absolute left-0 right-0 top-1/2 hidden -translate-y-1/2 md:block">
          <div className="mx-auto h-px w-full max-w-6xl bg-primary/20" />
        </div>
      </div>
    </section>
  )
}
