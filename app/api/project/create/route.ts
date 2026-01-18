import { NextRequest, NextResponse } from 'next/server';
import { auth0 } from '@/lib/auth0';
import { connectToDatabase } from '@/lib/mongodb';
import { createProject, PROJECTS_COLLECTION } from '@/lib/models/Project';

export async function POST(request: NextRequest) {
  try {
    // Verify authentication
    const session = await auth0.getSession(request);

    if (!session || !session.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const userId = session.user.sub; // Auth0 user ID
    const username = session.user.email || session.user.name || userId;

    // Parse request body
    const body = await request.json();
    const { projectName } = body;

    if (!projectName || typeof projectName !== 'string') {
      return NextResponse.json(
        { error: 'Project name is required' },
        { status: 400 }
      );
    }

    // Validate project name
    if (projectName.length < 1 || projectName.length > 100) {
      return NextResponse.json(
        { error: 'Project name must be between 1 and 100 characters' },
        { status: 400 }
      );
    }

    // Connect to database
    const { db } = await connectToDatabase();
    const projectsCollection = db.collection(PROJECTS_COLLECTION);

    // Check if project with same name already exists for this user
    const existingProject = await projectsCollection.findOne({
      userId,
      projectName,
    });

    if (existingProject) {
      return NextResponse.json(
        { error: 'A project with this name already exists' },
        { status: 409 }
      );
    }

    // Create new project
    const newProject = createProject(userId, username, projectName);

    const result = await projectsCollection.insertOne(newProject);

    return NextResponse.json(
      {
        projectId: result.insertedId.toString(),
        project: {
          ...newProject,
          _id: result.insertedId,
        },
      },
      { status: 201 }
    );
  } catch (error) {
    console.error('Error creating project:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
