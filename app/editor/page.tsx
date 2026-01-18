'use client'

import { useState, useEffect } from 'react'
import Upload from "@/components/editor/upload"
import Timeline from "@/components/editor/timeline"
import PageContainer from "@/components/page-container"

interface Clip {
  clipNumber: number
  filename: string
  s3Url: string
  uploadedAt: string
}

interface Project {
  _id: string
  projectName: string
  status: 'uploading' | 'processing' | 'completed' | 'failed'
  clips: Clip[]
  gumloopOutput?: any[]
  finalVideoUrl?: string
  error?: string
}

export default function Editor() {
  const [projectId, setProjectId] = useState<string | null>(null)
  const [projectName, setProjectName] = useState('')
  const [project, setProject] = useState<Project | null>(null)

  // Poll project status when processing
  useEffect(() => {
    if (!projectId || project?.status === 'completed' || project?.status === 'failed') {
      return
    }

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/project/${projectId}`)
        if (response.ok) {
          const data = await response.json()
          setProject(data.project)

          // Stop polling if completed or failed
          if (data.project.status === 'completed' || data.project.status === 'failed') {
            clearInterval(pollInterval)
          }
        }
      } catch (error) {
        console.error('Error polling project:', error)
      }
    }, 3000) // Poll every 3 seconds

    return () => clearInterval(pollInterval)
  }, [projectId, project?.status])

  const handleProjectCreate = (id: string, name: string) => {
    setProjectId(id)
    setProjectName(name)
    setProject({
      _id: id,
      projectName: name,
      status: 'uploading',
      clips: [],
    })
  }

  const handleClipUploaded = (clip: Clip) => {
    setProject((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        clips: [...prev.clips, clip],
      }
    })
  }

  const handleProcessStart = async () => {
    if (!projectId) return

    try {
      const response = await fetch('http://127.0.0.1:8000/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ projectId }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to start processing')
      }

      // Update status to processing
      setProject((prev) => {
        if (!prev) return prev
        return {
          ...prev,
          status: 'processing',
        }
      })
    } catch (error) {
      console.error('Error starting processing:', error)
      alert(error instanceof Error ? error.message : 'Failed to start processing')
    }
  }

  return (
    <main className="min-h-screen bg-background py-8">
      <PageContainer>
        <div className="mb-6">
          <h1 className="text-4xl font-bold text-foreground">Video Editor</h1>
          <p className="text-muted-foreground mt-2">
            Create your video by uploading clips and processing them with AI
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Upload
            projectId={projectId}
            projectName={projectName}
            onProjectCreate={handleProjectCreate}
            clips={project?.clips || []}
            onClipUploaded={handleClipUploaded}
            onProcessStart={handleProcessStart}
          />

          <Timeline
            status={project?.status || 'uploading'}
            gumloopMatches={project?.gumloopOutput}
            finalVideoUrl={project?.finalVideoUrl}
            error={project?.error}
          />
        </div>
      </PageContainer>
    </main>
  )
}
