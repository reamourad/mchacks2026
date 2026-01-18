import Hero from "@/components/landing/hero"
import Features from "@/components/landing/features"
import PageContainer from "@/components/page-container"

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      <PageContainer>
        <Hero />
        <Features />
      </PageContainer>
    </main>
  )
}
