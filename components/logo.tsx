import Link from "next/link"
import Image from "next/image"

export default function Logo() {
  // If you have the actual image file, uncomment this and place your logo in public/logo.png
  // return (
  //   <Link href="/" className="flex items-center gap-3 hover:opacity-90 transition-opacity">
  //     <Image 
  //       src="/logo.png" 
  //       alt="Xpresso Logo" 
  //       width={120} 
  //       height={40}
  //       className="h-10 w-auto"
  //       priority
  //     />
  //   </Link>
  // )

  // SVG Logo (matches the description: clapboard icon + Xpresso text)
  return (
    <Link href="/" className="flex items-center gap-3 hover:opacity-90 transition-opacity">
      <svg
        width="48"
        height="40"
        viewBox="0 0 48 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="flex-shrink-0"
      >
        {/* Film Clapboard Icon */}
        <g stroke="#FFE95B" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round">
          {/* Top angled section with diagonal stripes */}
          <path d="M6 14 L22 8 L22 14 L6 18 Z" />
          <line x1="9" y1="12" x2="9" y2="16" />
          <line x1="12.5" y1="11.5" x2="12.5" y2="15.5" />
          <line x1="16" y1="11" x2="16" y2="15" />
          <line x1="19.5" y1="10.5" x2="19.5" y2="14.5" />
          
          {/* Main rectangular body */}
          <rect x="6" y="18" width="28" height="18" rx="1.5" />
          
          {/* Triangle play button inside clapboard */}
          <path d="M16 24 L16 32 L24 28 Z" strokeWidth="2" />
        </g>
      </svg>
      
      {/* Xpresso Text - Stylized serif font */}
      <span 
        className="text-2xl font-bold text-accent tracking-tight"
        style={{
          fontFamily: 'var(--font-playfair), serif',
          letterSpacing: '-0.01em',
          fontWeight: 700,
        }}
      >
        Xpresso
      </span>
    </Link>
  )
}
