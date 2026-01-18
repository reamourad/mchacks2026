import Hero from "@/components/landing/hero"
import HowItWorks from "@/components/landing/how-it-works"
import Pipeline from "@/components/landing/pipeline"
import Contact from "@/components/landing/contact"
import Footer from "@/components/landing/footer"
import PageContainer from "@/components/page-container"

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      <PageContainer>
        <Hero />
        <HowItWorks />
        <Pipeline />
        <Contact />
      </PageContainer>
      <Footer />
    </main>
  )
}
