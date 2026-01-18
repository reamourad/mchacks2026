export const PROJECTS_COLLECTION = "projects"

import type { ObjectId } from "mongodb"

export type Clip = {
  clipNumber: number
  s3Key: string
  s3Url: string
  uploadedAt: Date
  filename: string
  size: number
}

export type GumloopMatch = {
  segment_id: number
  segment_description: string
  segment_time: string
  matched_clip: string
  clip_timestamp: string
  reason: string
}

export type Project = {
  _id?: ObjectId
  userId: string
  username: string
  projectName: string
  clips: Clip[]
  status?: string
  gumloopOutput?: GumloopMatch[]
  finalVideoUrl?: string
  finalVideoS3Key?: string
  createdAt?: Date
  updatedAt?: Date
  error?: string
}

export function createProject(userId: string, username: string, projectName: string): Project {
  const now = new Date()
  return {
    userId,
    username,
    projectName,
    clips: [],
    status: "draft",
    createdAt: now,
    updatedAt: now,
  }
}
