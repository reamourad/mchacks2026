import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default function Features() {
  return (
    <section>
      <h2 className="mb-12 text-center text-3xl font-bold text-foreground">
        Features
      </h2>
      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Feature 1</CardTitle>
            <CardDescription>Description of feature 1</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">Feature content goes here</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Feature 2</CardTitle>
            <CardDescription>Description of feature 2</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">Feature content goes here</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Feature 3</CardTitle>
            <CardDescription>Description of feature 3</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">Feature content goes here</p>
          </CardContent>
        </Card>
      </div>
    </section>
  )
}
