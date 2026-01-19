'use client'

import { useState, useRef } from 'react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useUser } from '@auth0/nextjs-auth0/client'

interface Clip {
  clipNumber: number
  filename: string
  s3Url: string
  uploadedAt: string
}

interface UploadProps {
  projectId: string | null
  projectName: string
  onProjectCreate: (id: string, name: string) => void
  clips: Clip[]
  onClipUploaded: (clip: Clip) => void
  onProcessStart: () => void
}

export default function Upload({
  projectId,
  projectName: initialProjectName,
  onProjectCreate,
  clips,
  onClipUploaded,
  onProcessStart,
}: UploadProps) {
  const { user } = useUser()
  const [projectName, setProjectName] = useState(initialProjectName)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [creating, setCreating] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles(Array.from(e.target.files))
    }
  }

  const createProject = async () => {
    // TODO: Implement backend API call
    console.log('createProject not implemented')
  }

  const uploadFiles = async () => {
    // TODO: Implement backend API call
    console.log('uploadFiles not implemented')
  }

  if (!user) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Upload Clips</CardTitle>
          <CardDescription>Please log in to upload clips</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload Clips</CardTitle>
        <CardDescription>
          Create a project and upload your video clips
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Project Name Input */}
          {!projectId && (
            <div className="space-y-2">
              <label className="text-sm font-medium">Project Name</label>
              <div className="flex gap-2">
                <Input
                  type="text"
                  placeholder="Enter project name"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  disabled={creating}
                />
                <Button onClick={createProject} disabled={creating || !projectName.trim()}>
                  {creating ? 'Creating...' : 'Create Project'}
                </Button>
              </div>
            </div>
          )}

          {/* Project Info */}
          {projectId && (
            <div className="p-3 bg-muted rounded-md">
              <p className="text-sm font-medium">Project: {projectName}</p>
              <p className="text-xs text-muted-foreground">ID: {projectId}</p>
            </div>
          )}

          {/* File Upload */}
          {projectId && (
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Select Video Clips</label>
                <Input
                  ref={fileInputRef}
                  type="file"
                  accept="video/*"
                  multiple
                  onChange={handleFileSelect}
                  disabled={uploading}
                />
                {selectedFiles.length > 0 && (
                  <p className="text-sm text-muted-foreground">
                    {selectedFiles.length} file(s) selected
                  </p>
                )}
              </div>

              <Button
                onClick={uploadFiles}
                disabled={uploading || selectedFiles.length === 0}
                className="w-full"
              >
                {uploading ? 'Uploading...' : 'Upload Clips'}
              </Button>
            </div>
          )}

          {/* Uploaded Clips List */}
          {clips.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium">Uploaded Clips ({clips.length})</h3>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {clips.map((clip) => (
                  <div
                    key={clip.clipNumber}
                    className="p-2 border rounded-md text-sm flex justify-between items-center"
                  >
                    <span>
                      {clip.clipNumber}. {clip.filename}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(clip.uploadedAt).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>

              {/* Process Button */}
              <Button
                onClick={onProcessStart}
                className="w-full"
                variant="default"
              >
                Process Video
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
