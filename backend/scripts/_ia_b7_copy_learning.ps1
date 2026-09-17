# Batch7 self-learning tabs copy: DT -> tupu. Same machinery as batch5.
$ErrorActionPreference = 'Stop'
$dt = 'D:\gitcangku\xiaobaohaohao\DeepTutor\web'
$src = 'D:\gitcangku\deepassetlens\frontend\src'

$ctxMap = @{
  '@/context/UnifiedChatContext'  = 'pages/tutor/h5/h5shared/UnifiedChatContext'
  '@/context/QuizFollowupContext' = 'pages/tutor/h5/h5shared/QuizFollowupContext'
}

$files = @(
  'app/(workspace)/self-learning/components/ChapterTree.tsx>pages/tutor/learning/components/ChapterTree.tsx',
  'app/(workspace)/self-learning/components/ChapterTabs.tsx>pages/tutor/learning/components/ChapterTabs.tsx',
  'app/(workspace)/self-learning/components/TabExportToolbar.tsx>pages/tutor/learning/components/TabExportToolbar.tsx',
  'app/(workspace)/self-learning/components/tabs/OriginalTextTab.tsx>pages/tutor/learning/components/tabs/OriginalTextTab.tsx',
  'app/(workspace)/self-learning/components/tabs/KnowledgePointsTab.tsx>pages/tutor/learning/components/tabs/KnowledgePointsTab.tsx',
  'app/(workspace)/self-learning/components/tabs/InternalBooksTab.tsx>pages/tutor/learning/components/tabs/InternalBooksTab.tsx',
  'app/(workspace)/self-learning/components/tabs/WrongQuestionsTab.tsx>pages/tutor/learning/components/tabs/WrongQuestionsTab.tsx',
  'app/(workspace)/self-learning/components/tabs/CoursewareTab.tsx>pages/tutor/learning/components/tabs/CoursewareTab.tsx',
  'app/(workspace)/self-learning/components/tabs/ExerciseTab.tsx>pages/tutor/learning/components/tabs/ExerciseTab.tsx',
  'app/(workspace)/self-learning/components/tabs/NotesTab.tsx>pages/tutor/learning/components/tabs/NotesTab.tsx',
  'app/(workspace)/self-learning/components/tabs/MemoryTab.tsx>pages/tutor/learning/components/tabs/MemoryTab.tsx',
  'app/(workspace)/self-learning/components/tabs/AIResourceTab.tsx>pages/tutor/learning/components/tabs/AIResourceTab.tsx',
  'app/(workspace)/self-learning/components/tabs/VoiceVideoTab.tsx>pages/tutor/learning/components/tabs/VoiceVideoTab.tsx',
  'app/(workspace)/self-learning/components/tabs/ReciteTab.tsx>pages/tutor/learning/components/tabs/ReciteTab.tsx',
  'app/(workspace)/self-learning/page.tsx>pages/tutor/learning/SelfLearning.tsx',
  'lib/self-learning-api.ts>lib/self-learning-api.ts',
  'lib/recite-diff.ts>lib/recite-diff.ts',
  'components/curriculum/KpRelationGraph.tsx>components/curriculum/KpRelationGraph.tsx',
  'components/curriculum/MathWidget.tsx>components/curriculum/MathWidget.tsx',
  'components/mother-questions/MotherQuestionFields.tsx>components/mother-questions/MotherQuestionFields.tsx'
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
  $c = $c -replace 'import \{ useSearchParams, useRouter \} from "next/navigation";', 'import { useSearchParams } from "react-router-dom";'
  $c = $c -replace 'import \{ useRouter \} from "next/navigation";', 'import { useNavigate } from "react-router-dom";'
  $c = $c -replace 'import \{ useSearchParams \} from "next/navigation";', 'import { useSearchParams } from "react-router-dom";'
  $left = [regex]::Matches($c, 'from "(@/|next/)')
  foreach ($l in $left) { $warns += "LEFT $dest :: $($l.Value)" }
  [System.IO.File]::WriteAllText($tp, $c, (New-Object System.Text.UTF8Encoding($false)))
  $done++
}

Write-Output "copied: $done files"
$warns | Select-Object -First 20
