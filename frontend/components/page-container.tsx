import { cn } from "@/lib/utils"
import { ReactNode } from "react"

interface PageContainerProps {
  children: ReactNode
  className?: string
}

export default function PageContainer({ children, className }: PageContainerProps) {
  return (
    <div className={cn(
      "mx-auto w-full max-w-7xl px-6 md:px-12",
      "bg-background",
      "space-y-24",
      className
    )}>
      {children}
    </div>
  )
}
