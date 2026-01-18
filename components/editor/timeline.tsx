import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"

export default function Timeline() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Timeline</CardTitle>
        <CardDescription>Your project timeline</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <div className="mb-2 flex justify-between text-sm">
              <span>Progress</span>
              <span>50%</span>
            </div>
            <Progress value={50} />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
