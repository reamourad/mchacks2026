import Upload from "@/components/editor/upload"
import Timeline from "@/components/editor/timeline"
import PageContainer from "@/components/page-container"

export default function Editor() {
  return (
    <main className="min-h-screen bg-background py-8">
      <PageContainer>
        <div>
          <h1 className="text-4xl font-bold text-foreground">Editor</h1>
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          <Upload />
          <Timeline />
        </div>
      </PageContainer>
    </main>
  )
}
