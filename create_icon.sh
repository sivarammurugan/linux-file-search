#!/bin/bash
# Create a simple SVG icon for File Search app

cat > ~/.local/share/icons/filesearch.svg << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<svg width="48" height="48" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
  <!-- Background circle -->
  <circle cx="24" cy="24" r="22" fill="#4A90E2" stroke="#2E5BBA" stroke-width="2"/>
  
  <!-- Magnifying glass -->
  <circle cx="18" cy="18" r="10" fill="none" stroke="white" stroke-width="3"/>
  <line x1="26" y1="26" x2="36" y2="36" stroke="white" stroke-width="3" stroke-linecap="round"/>
  
  <!-- File lines inside magnifying glass -->
  <line x1="14" y1="15" x2="22" y2="15" stroke="white" stroke-width="1.5" opacity="0.8"/>
  <line x1="14" y1="18" x2="20" y2="18" stroke="white" stroke-width="1.5" opacity="0.8"/>
  <line x1="14" y1="21" x2="22" y2="21" stroke="white" stroke-width="1.5" opacity="0.8"/>
  
  <!-- Lightning bolt for "fast" -->
  <path d="M32 8 L28 16 L32 16 L28 24 L36 14 L32 14 Z" fill="#FFD700" stroke="#FFA500" stroke-width="1"/>
</svg>
EOF
