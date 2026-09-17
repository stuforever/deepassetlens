# Batch2.3 component copy: DT -> tupu. Rewrite @/ aliases to relative paths,
# shim next/dynamic via React.lazy, swap next/link to react-router-dom.
# ASCII-only on purpose (PS5.1 no-BOM ANSI trap).
$ErrorActionPreference = 'Stop'
$dt = 'D:\gitcangku\xiaobaohaohao\DeepTutor\web'
$src = 'D:\gitcangku\deepassetlens\frontend\src'

$ctxMap = @{
  '@/context/UnifiedChatContext'  = 'pages/tutor/h5/h5shared/UnifiedChatContext'
  '@/context/QuizFollowupContext' = 'pages/tutor/h5/h5shared/QuizFollowupContext'
}

$files = @(
  'components/chat/home/AgentSelector.tsx','components/chat/home/AskUserOptions.tsx','components/chat/home/CapabilityConfigCard.tsx',
  'components/chat/home/ChatComposer.tsx','components/chat/home/ChatMessages.tsx','components/chat/home/composer-field.tsx',
  'components/chat/home/ComposerInput.tsx','components/chat/home/ContextBudgetChip.tsx','components/chat/home/ContextReferenceTree.tsx',
  'components/chat/home/KnowledgeSelector.tsx','components/chat/home/ModelSelector.tsx','components/chat/home/PersonaSelector.tsx',
  'components/chat/home/SessionActivityPanel.tsx','components/chat/home/SessionLoadingView.tsx','components/chat/home/SessionViewerPanel.tsx',
  'components/chat/home/SimpleComposerInput.tsx','components/chat/home/SubagentRunTranscript.tsx','components/chat/home/SubagentTabBody.tsx',
  'components/chat/home/TurnNavigator.tsx',
  'components/chat/HistorySessionPicker.tsx','components/chat/QuestionBankPicker.tsx','components/chat/space/ChatSpaceMenu.tsx',
  'components/chat/preview/previewerFor.ts','components/chat/preview/FilePreviewDrawer.tsx',
  'components/quiz/QuizViewer.tsx','components/quiz/QuizConfigPanel.tsx','components/quiz/QuizFollowupTabBody.tsx','components/quiz/FollowupChatComposer.tsx',
  'components/visualize/VisualizationViewer.tsx','components/visualize/VisualizeConfigPanel.tsx',
  'components/research/ResearchOutlineEditor.tsx','components/research/ResearchConfigPanel.tsx',
  'components/math-animator/MathAnimatorViewer.tsx','components/Geogebra.tsx',
  'components/common/PickerHeader.tsx','components/common/PickerShell.tsx','components/common/ProviderIcon.tsx','components/common/Tooltip.tsx',
  'hooks/useConnectedAgentKinds.ts','hooks/use-linger-expand.ts','hooks/useVoiceAutoplay.ts','hooks/useVoiceRecorder.ts','hooks/useSmoothStreamText.ts',
  'lib/book-api.ts','lib/book-references.ts','lib/book-types.ts','lib/book-ws-operation.ts','lib/chat-outline.ts','lib/code-languages.ts',
  'lib/iframe-html.ts','lib/math-animator-types.ts','lib/message-branches.ts','lib/message-content.ts','lib/notebook-selection-types.ts',
  'lib/personas-api.ts','lib/picker-origin.ts','lib/quiz-judge.ts','lib/quiz-question-type.ts','lib/quiz-types.ts','lib/research-types.ts',
  'lib/session-activity.ts','lib/session-api.ts','lib/space-items.ts','lib/visualize-types.ts',
  'components/notebook/NotebookRecordPicker.tsx','components/notebook/NotebookSelector.tsx','components/notebook/useNotebookSelection.ts',
  'components/chat/PersonaPicker.tsx','components/chat/MemoryPicker.tsx','components/chat/BookReferencePicker.tsx','components/chat/MyAgentsPicker.tsx',
  'lib/chat-import/index.ts','lib/chat-import/types.ts','lib/chat-import/agent-store.ts','lib/chat-import/attribution.ts','lib/imports-api.ts',
  'lib/playground-config.ts','lib/tools-settings.ts','hooks/useMeasuredHeight.ts'
)

$previewers = Get-ChildItem "$dt/components/chat/preview/previewers" -Filter "*.ts*"

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
foreach ($f in $files) {
  $sp = Join-Path $dt ($f -replace '/', '\')
  if (-not (Test-Path $sp)) { $warns += "SRCDIE $f"; continue }
  $tp = Join-Path $src ($f -replace '/', '\')
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
  foreach ($l in $left) { $warns += "LEFT $f :: $($l.Value)" }
  [System.IO.File]::WriteAllText($tp, $c, (New-Object System.Text.UTF8Encoding($false)))
  $done++
}

foreach ($pv in $previewers) {
  $tp = Join-Path $src "components/chat/preview/previewers/$($pv.Name)"
  $tdir = Split-Path $tp -Parent
  New-Item -ItemType Directory -Force -Path $tdir | Out-Null
  $c = [System.IO.File]::ReadAllText($pv.FullName, [System.Text.Encoding]::UTF8)
  $c = Rewrite-Aliases $c $tdir
  if ($c -match 'from "next/dynamic"') {
    $shim = 'import { lazy } from "react";' + "`r`n" + '// next/dynamic -> React.lazy shim (CRA has no SSR; ssr:false is a no-op). Registered in engine ledger E-20.' + "`r`n" + 'const dynamic = (loader: () => Promise<any>, _opts?: Record<string, unknown>) => lazy(loader);'
    $c = $c -replace 'import dynamic from "next/dynamic";', $shim
  }
  $c = $c -replace 'import Link from "next/link";', 'import { Link } from "react-router-dom";'
  [System.IO.File]::WriteAllText($tp, $c, (New-Object System.Text.UTF8Encoding($false)))
  $done++
}

New-Item -ItemType Directory -Force -Path "$src/locales/en", "$src/locales/zh" | Out-Null
Copy-Item "$dt/locales/en/app.json" "$src/locales/en/app.json" -Force
Copy-Item "$dt/locales/zh/app.json" "$src/locales/zh/app.json" -Force

Write-Output "copied: $done files"
$warns | Select-Object -First 20
