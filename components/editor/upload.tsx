import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default function Upload() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload</CardTitle>
        <CardDescription>Upload your files here</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <Input type="file" />
          <Button>Upload</Button>
        </div>
      </CardContent>
    </Card>
  )
}
