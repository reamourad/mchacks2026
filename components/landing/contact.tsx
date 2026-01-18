export default function Contact() {
  return (
    <section id="contact" className="py-12">
      <div className="mx-auto w-full max-w-4xl rounded-2xl border border-foreground/10 bg-black/20 px-6 py-10 backdrop-blur-sm md:px-10">
        <h2 className="text-3xl font-semibold text-foreground md:text-4xl" style={{ fontFamily: "var(--font-slogan)" }}>
          Contact us
        </h2>
        <p className="mt-4 max-w-2xl text-sm text-foreground/70 md:text-base">
          Have a question, feedback, or want to collaborate? Send us a message and we’ll get back to you.
        </p>

        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <div>
            <div className="text-xs font-semibold text-foreground/70">Email</div>
            <a
              className="mt-1 inline-block text-sm text-foreground/70 transition-colors hover:text-primary"
              href="mailto:hello@xpresso.video"
            >
              hello@xpresso.video
            </a>
          </div>
          <div>
            <div className="text-xs font-semibold text-foreground/70">Social</div>
            <div className="mt-2 text-sm text-foreground/70">@xpresso</div>
          </div>
        </div>
      </div>
    </section>
  )
}
