export default function HowItWorks() {
  return (
    <section className="py-12">
      <h2 className="mb-10 text-center text-3xl font-bold text-foreground md:text-4xl">
        See Xpresso in Action
      </h2>

      <div className="relative mx-auto grid w-full max-w-6xl items-center gap-10 md:grid-cols-3 md:gap-12">
        <svg
          className="pointer-events-none absolute inset-0 hidden h-full w-full md:block"
          viewBox="0 0 1000 400"
          preserveAspectRatio="none"
        >
          <defs>
            <marker
              id="arrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="8"
              markerHeight="8"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#F1FAEE" />
            </marker>
          </defs>

          <path
            d="M 460 120 C 380 120, 340 120, 300 120"
            stroke="#F1FAEE"
            strokeWidth="2"
            fill="none"
            markerEnd="url(#arrow)"
            strokeLinecap="round"
          />
          <path
            d="M 460 240 C 380 240, 340 240, 300 240"
            stroke="#F1FAEE"
            strokeWidth="2"
            fill="none"
            markerEnd="url(#arrow)"
            strokeLinecap="round"
          />

          <path
            d="M 540 110 C 620 110, 660 110, 700 110"
            stroke="#F1FAEE"
            strokeWidth="2"
            fill="none"
            markerEnd="url(#arrow)"
            strokeLinecap="round"
          />
          <path
            d="M 540 200 C 620 200, 660 200, 700 200"
            stroke="#F1FAEE"
            strokeWidth="2"
            fill="none"
            markerEnd="url(#arrow)"
            strokeLinecap="round"
          />
          <path
            d="M 540 290 C 620 290, 660 290, 700 290"
            stroke="#F1FAEE"
            strokeWidth="2"
            fill="none"
            markerEnd="url(#arrow)"
            strokeLinecap="round"
          />
        </svg>

        <div className="relative z-10 flex flex-col gap-6">
          <div className="w-full rounded-xl border border-foreground/20 bg-background/40 px-5 py-4 backdrop-blur-sm">
            <div className="text-lg font-semibold text-foreground">sections generator</div>
          </div>
          <div className="w-full rounded-xl border border-foreground/20 bg-background/40 px-5 py-4 backdrop-blur-sm">
            <div className="text-lg font-semibold text-foreground">Voice over recognition</div>
          </div>
        </div>

        <div className="relative z-10 mx-auto w-full max-w-[340px]">
          <div className="relative overflow-hidden rounded-[2.25rem] border border-foreground/25 bg-background/40 p-3 shadow-[0_0_0_1px_rgba(241,250,238,0.08)] backdrop-blur-sm">
            <div className="overflow-hidden rounded-[1.75rem] bg-black">
              <div className="aspect-[9/16] w-full">
                <video
                  className="h-full w-full object-cover"
                  src="/xpresso-demo.mp4"
                  controls
                  playsInline
                />
              </div>
            </div>
          </div>
        </div>

        <div className="relative z-10 flex flex-col gap-6">
          <div className="w-full rounded-xl border border-foreground/20 bg-background/40 px-5 py-4 backdrop-blur-sm">
            <div className="text-lg font-semibold text-foreground">video recognition</div>
          </div>
          <div className="w-full rounded-xl border border-foreground/20 bg-background/40 px-5 py-4 backdrop-blur-sm">
            <div className="text-lg font-semibold text-foreground">cool FONTS</div>
          </div>
          <div className="w-full rounded-xl border border-foreground/20 bg-background/40 px-5 py-4 backdrop-blur-sm">
            <div className="text-lg font-semibold text-foreground">captions</div>
          </div>
        </div>
      </div>
    </section>
  )
}
