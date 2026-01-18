'use client'

import { useState } from 'react'
import { createVideoWithBackend } from '@/lib/services/backend-video'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'

interface VideoProcessorProps {
  projectId: string
  projectName: string
  username: string
  clips: Array<{ s3Url: string; filename: string; clipNumber: number }>
  gumloopMatches: any[]
  onComplete: (finalVideoUrl: string) => void
  onError: (error: string) => void
}

export default function VideoProcessor({
  projectId,
  projectName,
  username,
  clips,
  gumloopMatches,
  onComplete,
  onError,
}: VideoProcessorProps) {
  const [processing, setProcessing] = useState(false)
  const [stage, setStage] = useState('')
  const [progress, setProgress] = useState(0)

  const processVideo = async () => {
    setProcessing(true)
    setStage('Starting backend processing...')
    setProgress(0)

    try {
      // Call backend to process video
      setStage('Sending request to backend...')
      setProgress(10)

      const result = await createVideoWithBackend(
        username,
        projectName,
        gumloopMatches
      )

      setStage('Video processing complete!')
      setProgress(90)

      // Update project in database
      await fetch(`/api/project/${projectId}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          finalVideoUrl: result.videoUrl,
          finalVideoS3Key: result.s3Key
        }),
      })

      setStage('Complete!')
      setProgress(100)

      onComplete(result.videoUrl)
    } catch (error) {
      console.error('Error processing video:', error)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      onError(errorMessage)

      // Update project status to failed
      await fetch(`/api/project/${projectId}/fail`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error: errorMessage }),
      })
    } finally {
      setProcessing(false)
    }
  }

  if (!processing) {
    return (
      <Button onClick={processVideo} className="w-full">
        Process Video
      </Button>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <div className="mb-2 flex justify-between text-sm">
          <span className="font-medium">{stage}</span>
          <span className="text-muted-foreground">{progress}%</span>
        </div>
        <Progress value={progress} />
      </div>
      <p className="text-xs text-muted-foreground">
        Processing video on backend server...
      </p>
    </div>
  )
}
