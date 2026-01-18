import { NextRequest, NextResponse } from 'next/server';
import { auth0 } from '@/lib/auth0';
import { connectToDatabase } from '@/lib/mongodb';
import { PROJECTS_COLLECTION, Clip } from '@/lib/models/Project';
import { uploadToS3, generateS3Key, getPresignedUrl } from '@/lib/s3';
import { ObjectId } from 'mongodb';

export async function POST(request: NextRequest) {
  try {
    // Verify authentication
    const session = await auth0.getSession(request);

    if (!session || !session.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const userId = session.user.sub;
    const username = session.user.email || session.user.name || userId;

    // Parse multipart form data
    const formData = await request.formData();
    const projectId = formData.get('projectId') as string;
    const file = formData.get('file') as File;

    if (!projectId || !file) {
      return NextResponse.json(
        { error: 'Project ID and file are required' },
        { status: 400 }
      );
    }

    // Validate file type
    if (!file.type.startsWith('video/')) {
      return NextResponse.json(
        { error: 'Only video files are allowed' },
        { status: 400 }
      );
    }

    // Validate file size (max 500MB)
    const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500MB
    if (file.size > MAX_FILE_SIZE) {
      return NextResponse.json(
        { error: 'File size must be less than 500MB' },
        { status: 400 }
      );
    }

    // Connect to database
    const { db } = await connectToDatabase();
    const projectsCollection = db.collection(PROJECTS_COLLECTION);

    // Find project and verify ownership
    const project = await projectsCollection.findOne({
      _id: new ObjectId(projectId),
      userId,
    });

    if (!project) {
      return NextResponse.json(
        { error: 'Project not found or access denied' },
        { status: 404 }
      );
    }

    // Determine clip number (auto-increment)
    const clipNumber = project.clips.length + 1;

    // Generate S3 key
    const s3Key = generateS3Key(username, project.projectName, clipNumber);

    // Convert file to buffer
    const arrayBuffer = await file.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    // Upload to S3
    const s3Url = await uploadToS3(buffer, s3Key, file.type);

    // Get presigned URL for viewing
    const presignedUrl = await getPresignedUrl(s3Key);

    // Create clip object
    const newClip: Clip = {
      clipNumber,
      s3Key,
      s3Url: presignedUrl,
      uploadedAt: new Date(),
      filename: file.name,
      size: file.size,
    };

    // Update project in database
    await projectsCollection.updateOne(
      { _id: new ObjectId(projectId) },
      {
        $push: { clips: newClip } as any,
        $set: { updatedAt: new Date() },
      }
    );

    return NextResponse.json(
      {
        message: 'File uploaded successfully',
        clip: newClip,
        clipNumber,
      },
      { status: 200 }
    );
  } catch (error) {
    console.error('Error uploading file:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
