'use client'

import { useMemo, useRef, useState, useEffect } from 'react'
import { useUser } from '@auth0/nextjs-auth0/client'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Download, Search, Settings, Type, Upload as UploadIcon } from "lucide-react"

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
  const { user, isLoading } = useUser()
  const [projectId, setProjectId] = useState<string | null>(null)
  const [projectName, setProjectName] = useState('')
  const [project, setProject] = useState<Project | null>(null)
  const [creating, setCreating] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [aspect, setAspect] = useState<'16:9' | '9:16'>('16:9')
  const [isFontPickerOpen, setIsFontPickerOpen] = useState(false)
  const [fontSearch, setFontSearch] = useState('')
  const [selectedFont, setSelectedFont] = useState<
    | 'Playfair Display'
    | 'Bowlby One SC'
    | 'Playwrite NG Modern'
    | 'Cherry Bomb One'
    | 'Limelight'
    | 'Monsieur La Doulaise'
  >('Playfair Display')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const fontOptions = useMemo(
    () =>
      [
        {
          label: 'Playfair Display' as const,
          fontFamily: 'var(--font-playfair)',
        },
        {
          label: 'Bowlby One SC' as const,
          fontFamily: 'var(--font-bowlby)',
        },
        {
          label: 'Playwrite NG Modern' as const,
          fontFamily: '"Playwrite NG Modern"',
        },
        {
          label: 'Cherry Bomb One' as const,
          fontFamily: 'var(--font-cherry-bomb-one)',
        },
        {
          label: 'Limelight' as const,
          fontFamily: 'var(--font-limelight)',
        },
        {
          label: 'Monsieur La Doulaise' as const,
          fontFamily: 'var(--font-monsieur-la-doulaise)',
        },
      ],
    []
  )

  const selectedFontFamily = useMemo(() => {
    return fontOptions.find((f) => f.label === selectedFont)?.fontFamily
  }, [fontOptions, selectedFont])

  const filteredFontOptions = useMemo(() => {
    const q = fontSearch.trim().toLowerCase()
    if (!q) return fontOptions
    return fontOptions.filter((f) => f.label.toLowerCase().includes(q))
  }, [fontOptions, fontSearch])

  const clips = useMemo(() => project?.clips || [], [project?.clips])

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
      const response = await fetch('/api/process', {
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

  const createProject = async (nameOverride?: string): Promise<string | null> => {
    const nameToUse = (nameOverride ?? projectName).trim()
    if (!nameToUse) return null

    setCreating(true)
    try {
      const response = await fetch('/api/project/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ projectName: nameToUse }),
      })

      if (!response.ok) {
        const error = await response.json().catch(() => ({}))
        throw new Error(error.error || 'Failed to create project')
      }

      const data = await response.json()
      handleProjectCreate(data.projectId, nameToUse)
      return data.projectId as string
    } catch (error) {
      console.error('Error creating project:', error)
      alert(error instanceof Error ? error.message : 'Failed to create project')
      return null
    } finally {
      setCreating(false)
    }
  }

  const uploadFiles = async (filesOverride?: File[]) => {
    const filesToUpload = filesOverride ?? selectedFiles
    if (filesToUpload.length === 0) {
      alert('Select at least one video file')
      return
    }

    let ensuredProjectId = projectId
    if (!ensuredProjectId) {
      const fallbackName = projectName.trim() || `Untitled Project ${new Date().toLocaleString()}`
      setProjectName(fallbackName)
      const createdId = await createProject(fallbackName)
      ensuredProjectId = createdId
    }

    if (!ensuredProjectId) return

    setUploading(true)
    try {
      for (const file of filesToUpload) {
        const formData = new FormData()
        formData.append('projectId', ensuredProjectId)
        formData.append('file', file)

        const response = await fetch('/api/upload', {
          method: 'POST',
          body: formData,
        })

        if (!response.ok) {
          const error = await response.json().catch(() => ({}))
          throw new Error(error.error || `Failed to upload ${file.name}`)
        }

        const data = await response.json()
        handleClipUploaded(data.clip)
      }

      setSelectedFiles([])
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch (error) {
      console.error('Error uploading files:', error)
      alert(error instanceof Error ? error.message : 'Failed to upload files')
    } finally {
      setUploading(false)
    }
  }

  const handleCenterUploadClick = () => {
    if (isLoading) return
    if (!user) {
      window.location.href = '/api/auth/login'
      return
    }
    fileInputRef.current?.click()
  }

  const downloadFinalVideo = () => {
    if (project?.finalVideoUrl) {
      window.open(project.finalVideoUrl, '_blank')
    }
  }

  return (
    <main className="min-h-screen bg-[#151E23] text-foreground">
      <div className="flex h-screen flex-col">
        <header className="flex h-14 items-center justify-between border-b border-foreground/10 px-4">
          <div />

          <div className="flex items-center gap-2 rounded-lg border border-foreground/10 bg-black/20 p-1">
            <button
              type="button"
              onClick={() => setAspect('16:9')}
              className={`rounded-md px-3 py-1 text-xs transition-colors ${
                aspect === '16:9'
                  ? 'bg-primary text-[#151E23]'
                  : 'text-foreground/70 hover:bg-white/5'
              }`}
            >
              16:9
            </button>
            <button
              type="button"
              onClick={() => setAspect('9:16')}
              className={`rounded-md px-3 py-1 text-xs transition-colors ${
                aspect === '9:16'
                  ? 'bg-primary text-[#151E23]'
                  : 'text-foreground/70 hover:bg-white/5'
              }`}
            >
              9:16
            </button>
          </div>

          <Button
            onClick={downloadFinalVideo}
            disabled={!project?.finalVideoUrl}
            className="gap-2"
          >
            <Download className="h-4 w-4" />
            Download
          </Button>
        </header>

        <div className="flex min-h-0 flex-1">
          <aside className="hidden w-[300px] flex-shrink-0 border-r border-foreground/10 bg-black/20 p-4 md:block">
            <div className="mb-4 flex items-center justify-between">
              <div className="text-sm font-semibold">Fonts Library</div>
            </div>

            <div className="mb-4 flex items-center gap-2 rounded-lg border border-foreground/10 bg-black/20 px-3 py-2">
              <Search className="h-4 w-4 text-foreground/60" />
              <input
                className="w-full bg-transparent text-sm text-foreground outline-none placeholder:text-foreground/40"
                placeholder="Search fonts..."
                value={fontSearch}
                onChange={(e) => setFontSearch(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              {isFontPickerOpen ? (
                filteredFontOptions.length === 0 ? (
                  <div className="rounded-lg border border-foreground/10 bg-black/20 px-3 py-3 text-sm text-foreground/60">
                    No fonts found
                  </div>
                ) : (
                  filteredFontOptions.map((font) => {
                    const isSelected = font.label === selectedFont
                    return (
                      <button
                        key={font.label}
                        type="button"
                        onClick={() => setSelectedFont(font.label)}
                        className={`w-full rounded-lg border px-3 py-3 text-left transition-colors ${
                          isSelected
                            ? 'border-primary/40 bg-black/20'
                            : 'border-foreground/10 bg-black/20 hover:bg-white/5'
                        }`}
                      >
                        <div className="text-[10px] uppercase tracking-wider text-foreground/50">Font</div>
                        <div className="mt-1 text-sm font-semibold text-foreground">{font.label}</div>
                        <div
                          className="mt-1 text-xs text-foreground/60"
                          style={{ fontFamily: font.fontFamily }}
                        >
                          The quick brown fox jumps...
                        </div>
                      </button>
                    )
                  })
                )
              ) : (
                <div className="rounded-lg border border-foreground/10 bg-black/20 px-3 py-3 text-sm text-foreground/60">
                  Press the <span className="text-foreground">T</span> tool to browse fonts
                </div>
              )}
            </div>

            <div className="mt-6 border-t border-foreground/10 pt-4">
              {isLoading ? (
                <div className="text-xs text-foreground/60">Loading...</div>
              ) : !user ? (
                <div className="text-xs text-foreground/60">Log in to upload clips</div>
              ) : (
                <div className="space-y-3">
                  {!projectId && (
                    <div className="space-y-2">
                      <div className="text-xs font-semibold text-foreground/80">Project</div>
                      <div className="flex gap-2">
                        <Input
                          value={projectName}
                          onChange={(e) => setProjectName(e.target.value)}
                          placeholder="Project name"
                          disabled={creating}
                        />
                        <Button onClick={() => void createProject()} disabled={creating || !projectName.trim()}>
                          {creating ? '...' : 'Create'}
                        </Button>
                      </div>
                    </div>
                  )}

                  {projectId && (
                    <div className="space-y-2">
                      <div className="text-xs text-foreground/60">Project: <span className="text-foreground/90">{projectName}</span></div>
                      <Input
                        ref={fileInputRef}
                        type="file"
                        accept="video/*"
                        multiple
                        onChange={(e) => setSelectedFiles(e.target.files ? Array.from(e.target.files) : [])}
                        disabled={uploading}
                      />
                      <Button
                        onClick={() => void uploadFiles()}
                        disabled={uploading || selectedFiles.length === 0}
                        className="w-full"
                      >
                        {uploading ? 'Uploading...' : 'Upload Clips'}
                      </Button>

                      <Button
                        onClick={handleProcessStart}
                        disabled={clips.length === 0 || project?.status === 'processing'}
                        className="w-full"
                      >
                        {project?.status === 'processing' ? 'Processing...' : 'Process Video'}
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </aside>

          <section className="relative flex min-h-0 flex-1 flex-col">
            <div className="relative flex min-h-0 flex-1 items-center justify-center p-6">
              <div className="absolute inset-0 opacity-30" style={{
                backgroundImage:
                  'radial-gradient(circle at 1px 1px, rgba(241,250,238,0.15) 1px, transparent 0)',
                backgroundSize: '22px 22px',
              }} />

              <div
                className={`relative rounded-xl border border-foreground/10 bg-black/30 p-6 shadow-[0_30px_80px_rgba(0,0,0,0.6)] ${
                  aspect === '16:9' ? 'w-full max-w-4xl' : 'w-auto max-w-full'
                }`}
              >
                <div
                  className={`mx-auto overflow-hidden rounded-lg border border-foreground/10 bg-black/40 ${
                    aspect === '16:9'
                      ? 'w-full'
                      : 'w-auto'
                  }`}
                >
                  <div
                    className={`mx-auto max-h-[calc(100vh-56px-240px-48px)] ${
                      aspect === '16:9'
                        ? 'aspect-video w-full'
                        : 'aspect-[9/16] h-[calc(100vh-56px-240px-48px)] w-auto max-w-full'
                    }`}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="video/*"
                      multiple
                      className="hidden"
                      onChange={(e) => {
                        const files = e.target.files ? Array.from(e.target.files) : []
                        setSelectedFiles(files)
                        if (files.length > 0) void uploadFiles(files)
                      }}
                      disabled={uploading}
                    />
                    <div className="pointer-events-none absolute inset-0 flex items-start justify-center pt-10">
                      <div
                        className="rounded-lg border border-foreground/10 bg-black/30 px-4 py-2 text-2xl text-foreground shadow-sm"
                        style={{ fontFamily: selectedFontFamily }}
                      >
                        Add text
                      </div>
                    </div>
                    {project?.finalVideoUrl ? (
                      <video
                        className="h-full w-full object-cover"
                        src={project.finalVideoUrl}
                        controls
                        playsInline
                      />
                    ) : (
                      <div className="flex h-full w-full flex-col items-center justify-center gap-4 text-sm text-foreground/60">
                        <Button
                          type="button"
                          onClick={handleCenterUploadClick}
                          disabled={uploading || isLoading}
                          className="h-12 rounded-xl px-6"
                        >
                          {uploading ? 'Uploading...' : 'Upload video'}
                        </Button>
                        <div>Upload clips to preview your edit here</div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="absolute right-4 top-1/2 hidden -translate-y-1/2 flex-col gap-2 md:flex">
                <button className="flex h-11 w-11 items-center justify-center rounded-xl border border-foreground/10 bg-black/25 text-foreground/80 hover:bg-white/5">
                  <Search className="h-5 w-5" />
                </button>
                <button
                  type="button"
                  onClick={() => setIsFontPickerOpen((v) => !v)}
                  className={`flex h-11 w-11 items-center justify-center rounded-xl border bg-black/25 hover:bg-white/5 ${
                    isFontPickerOpen
                      ? 'border-primary/40 text-primary'
                      : 'border-foreground/10 text-foreground/80'
                  }`}
                >
                  <Type className="h-5 w-5" />
                </button>
                <button className="flex h-11 w-11 items-center justify-center rounded-xl border border-foreground/10 bg-black/25 text-foreground/80 hover:bg-white/5">
                  <UploadIcon className="h-5 w-5" />
                </button>
                <button className="flex h-11 w-11 items-center justify-center rounded-xl border border-foreground/10 bg-black/25 text-foreground/80 hover:bg-white/5">
                  <Settings className="h-5 w-5" />
                </button>
              </div>
            </div>

            <div className="h-[240px] border-t border-foreground/10 bg-black/25">
              <div className="flex h-full flex-col">
                <div className="flex items-center justify-between border-b border-foreground/10 px-4 py-2">
                  <div className="text-xs text-foreground/70">
                    {project?.status ? `Status: ${project.status}` : 'Status: idle'}
                  </div>
                  <div className="text-xs text-foreground/50">Timeline</div>
                </div>

                <div className="min-h-0 flex-1 overflow-auto p-4">
                  {clips.length === 0 ? (
                    <div className="text-sm text-foreground/60">No clips yet. Upload clips to start.</div>
                  ) : (
                    <div className="space-y-3">
                      {clips.map((clip) => (
                        <div key={clip.clipNumber} className="rounded-lg border border-foreground/10 bg-black/20 px-4 py-3">
                          <div className="flex items-center justify-between">
                            <div className="text-sm font-medium">{clip.clipNumber}. {clip.filename}</div>
                            <div className="text-xs text-foreground/50">{new Date(clip.uploadedAt).toLocaleTimeString()}</div>
                          </div>
                          <div className="mt-2 h-2 w-full rounded-full bg-white/5">
                            <div className="h-2 w-1/3 rounded-full bg-primary" />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>
  )
}
