# Batch5 book copy: DT -> tupu. Same machinery as batch2 (alias rewrite,
# next/dynamic shim, next/link swap). ASCII-only (PS5.1 no-BOM ANSI trap).
$ErrorActionPreference = 'Stop'
$dt = 'D:\gitcangku\xiaobaohaohao\DeepTutor\web'
$src = 'D:\gitcangku\deepassetlens\frontend\src'

$ctxMap = @{
  '@/context/UnifiedChatContext'  = 'pages/tutor/h5/h5shared/UnifiedChatContext'
  '@/context/QuizFollowupContext' = 'pages/tutor/h5/h5shared/QuizFollowupContext'
}

# book page.tsx -> pages/tutor/book/BookWorkbench.tsx; components verbatim;
# plus missing deps (usePageSpeech/notifications/lib book-progress/AppShellContext).
$files = @(
  'app/(workspace)/book/page.tsx>pages/tutor/book/BookWorkbench.tsx',
  'app/(workspace)/book/components/BookLibrary.tsx>pages/tutor/book/components/BookLibrary.tsx',
  'app/(workspace)/book/components/BookCreator.tsx>pages/tutor/book/components/BookCreator.tsx',
  'app/(workspace)/book/components/BookSidebar.tsx>pages/tutor/book/components/BookSidebar.tsx',
  'app/(workspace)/book/components/SpineEditor.tsx>pages/tutor/book/components/SpineEditor.tsx',
  'app/(workspace)/book/components/PageReader.tsx>pages/tutor/book/components/PageReader.tsx',
  'app/(workspace)/book/components/PageOutlineNav.tsx>pages/tutor/book/components/PageOutlineNav.tsx',
  'app/(workspace)/book/components/PageSpeechBar.tsx>pages/tutor/book/components/PageSpeechBar.tsx',
  'app/(workspace)/book/components/BookChatPanel.tsx>pages/tutor/book/components/BookChatPanel.tsx',
  'app/(workspace)/book/components/BookProgressTimeline.tsx>pages/tutor/book/components/BookProgressTimeline.tsx',
  'app/(workspace)/book/components/BookHealthBanner.tsx>pages/tutor/book/components/BookHealthBanner.tsx',
  'app/(workspace)/book/components/speech-segments.ts>pages/tutor/book/components/speech-segments.ts',
  'app/(workspace)/book/components/blocks/AnimationBlock.tsx>pages/tutor/book/components/blocks/AnimationBlock.tsx',
  'app/(workspace)/book/components/blocks/BlockRenderer.tsx>pages/tutor/book/components/blocks/BlockRenderer.tsx',
  'app/(workspace)/book/components/blocks/CalloutBlock.tsx>pages/tutor/book/components/blocks/CalloutBlock.tsx',
  'app/(workspace)/book/components/blocks/CodeBlock.tsx>pages/tutor/book/components/blocks/CodeBlock.tsx',
  'app/(workspace)/book/components/blocks/ConceptGraphBlock.tsx>pages/tutor/book/components/blocks/ConceptGraphBlock.tsx',
  'app/(workspace)/book/components/blocks/DeepDiveBlock.tsx>pages/tutor/book/components/blocks/DeepDiveBlock.tsx',
  'app/(workspace)/book/components/blocks/FigureBlock.tsx>pages/tutor/book/components/blocks/FigureBlock.tsx',
  'app/(workspace)/book/components/blocks/FlashCardsBlock.tsx>pages/tutor/book/components/blocks/FlashCardsBlock.tsx',
  'app/(workspace)/book/components/blocks/InteractiveBlock.tsx>pages/tutor/book/components/blocks/InteractiveBlock.tsx',
  'app/(workspace)/book/components/blocks/PlaceholderBlock.tsx>pages/tutor/book/components/blocks/PlaceholderBlock.tsx',
  'app/(workspace)/book/components/blocks/QuizBlock.tsx>pages/tutor/book/components/blocks/QuizBlock.tsx',
  'app/(workspace)/book/components/blocks/SectionBlock.tsx>pages/tutor/book/components/blocks/SectionBlock.tsx',
  'app/(workspace)/book/components/blocks/TextBlock.tsx>pages/tutor/book/components/blocks/TextBlock.tsx',
  'app/(workspace)/book/components/blocks/TimelineBlock.tsx>pages/tutor/book/components/blocks/TimelineBlock.tsx',
  'app/(workspace)/book/components/blocks/UserNoteBlock.tsx>pages/tutor/book/components/blocks/UserNoteBlock.tsx',
  'hooks/usePageSpeech.ts>hooks/usePageSpeech.ts',
  'lib/notifications.ts>lib/notifications.ts',
  'lib/book-progress.ts>lib/book-progress.ts',
  'context/AppShellContext.tsx>context/AppShellContext.tsx'
)

function Resolve-Rel([string]$fromDir, [string]$targetRel) {
  $targetAbs = Join-Path $src ($targetRel -replace '/', '\')
  $fromUri = [Uri]($fromDir.TrimEnd('\') + '\')
  $toUri = [Uri]($targetAbs.TrimEnd('\') + '\')
  $rel = $fromUri.MakeRelativeUri($toUri).ToString().TrimEnd('/')
  if (-not $rel.StartsWith('.')) { $rel = "./$rel" }
  if ($rel -eq './.') { $rel = '.' }
  return $rel
}

function Rewrite-Aliases([string]$c, [string]$tdir) {
  $c = [regex]::Replace($c, 'from "(@/[^"]+)"', {
    param($m)
    $spec = $m.Groups[1].Value
    if ($ctxMap.ContainsKey($spec)) { $targetRel = $ctxMap[$spec] } else { $targetRel = $spec.Substring(2) }
    $rel = Resolve-Rel $tdir $targetRel
    'from "' + $rel + '"'
  })
  $c = [regex]::Replace($c, 'import\("(@/[^"]+)"\)', {
    param($m)
    $spec = $m.Groups[1].Value
    if ($ctxMap.ContainsKey($spec)) { $targetRel = $ctxMap[$spec] } else { $targetRel = $spec.Substring(2) }
    $rel = Resolve-Rel $tdir $targetRel
    'import("' + $rel + '")'
  })
  return $c
}

$done = 0; $warns = @()
foreach ($entry in $files) {
  $parts = $entry -split '>'
  $f = $parts[0]; $dest = $parts[1]
  $sp = Join-Path $dt ($f -replace '/', '\')
  if (-not (Test-Path $sp)) { $warns += "SRCDIE $f"; continue }
  $tp = Join-Path $src ($dest -replace '/', '\')
  $tdir = Split-Path $tp -Parent
  New-Item -ItemType Directory -Force -Path $tdir | Out-Null
  $c = [System.IO.File]::ReadAllText($sp, [System.Text.Encoding]::UTF8)
  $c = Rewrite-Aliases $c $tdir
  if ($c -match 'from "next/dynamic"') {
    $shim = 'import { lazy } from "react";' + "`r`n" + '// next/dynamic -> React.lazy shim (CRA has no SSR; ssr:false is a no-op). Registered in engine ledger E-20.' + "`r`n" + 'const dynamic = (loader: () => Promise<any>, _opts?: Record<string, unknown>) => lazy(loader);'
    $c = $c -replace 'import dynamic from "next/dynamic";', $shim
  }
  $c = $c -replace 'import Link from "next/link";', 'import { Link } from "react-router-dom";'
  $left = [regex]::Matches($c, 'from "(@/|next/)')
  foreach ($l in $left) { $warns += "LEFT $dest :: $($l.Value)" }
  [System.IO.File]::WriteAllText($tp, $c, (New-Object System.Text.UTF8Encoding($false)))
  $done++
}

Write-Output "copied: $done files"
$warns | Select-Object -First 20
