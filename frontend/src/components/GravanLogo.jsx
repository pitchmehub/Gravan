import React from 'react'

export default function GravanLogo({
  height = 40,
  color = '#0E2A55',
  textColor = '#111111',
  className = '',
  style = {},
  ariaLabel = 'Gravan',
}) {
  return (
    <span
      className={`gravan-logo ${className}`}
      role="img"
      aria-label={ariaLabel}
      style={{ display: 'inline-flex', alignItems: 'center', lineHeight: 0, ...style }}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 520 160"
        height={height}
        width="auto"
        style={{ display: 'block' }}
      >
        <g fill="none" stroke={color} strokeWidth="10" strokeLinecap="round">
          <path d="M 105 45 A 55 55 0 1 0 105 135" />
          <line x1="80" y1="90" x2="115" y2="90" />
        </g>
        <text
          x="150"
          y="112"
          fontFamily="'Playfair Display', 'Cormorant Garamond', 'Times New Roman', serif"
          fontSize="92"
          fontWeight="500"
          fill={textColor}
          letterSpacing="-1"
        >
          ravan
        </text>
      </svg>
    </span>
  )
}
