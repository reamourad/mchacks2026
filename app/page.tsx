import Hero from "@/components/landing/hero"
import Features from "@/components/landing/features"
import HowItWorks from "@/components/landing/how-it-works"
import PageContainer from "@/components/page-container"

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      <PageContainer>
        <Hero />
        <HowItWorks />
        <Features />
      </PageContainer>
    </main>
  )
}
