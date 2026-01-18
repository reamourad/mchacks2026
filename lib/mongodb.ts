import { MongoClient } from "mongodb"

const uri = process.env.MONGODB_URI

if (!uri) {
  throw new Error("Missing MONGODB_URI env var")
}

const mongoUri: string = uri

let client: MongoClient | null = null

export async function connectToDatabase() {
  if (!client) {
    client = new MongoClient(mongoUri)
    await client.connect()
  }

  const dbName = process.env.MONGODB_DB
  const db = dbName ? client.db(dbName) : client.db()

  return { client, db }
}
