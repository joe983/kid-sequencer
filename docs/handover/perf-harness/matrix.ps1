param(
  [string]$Label,
  [string]$Css = '',
  [int]$Throttle = 4,
  [int]$Runs = 3,
  [int]$Fill = 120,
  [int]$Taps = 0,
  [int]$Secs = 6,
  [string]$Extra = '',
  [string]$Page = ''
)
if ($Page) { $env:PAGE = $Page } else { Remove-Item Env:PAGE -ErrorAction SilentlyContinue }
$sp = 'C:\Users\T789D~1.JOE\AppData\Local\Temp\claude\C--Users-T-Joe-DLTS-Documents-My-Projects-kid-sequencer-repo\8aa34674-bc21-47bf-972a-3990a0ffdc7c\scratchpad'
Remove-Item Env:TRACE -ErrorAction SilentlyContinue
if ($Css) { $env:INJECT_CSS = $Css } else { Remove-Item Env:INJECT_CSS -ErrorAction SilentlyContinue }
if ($Extra) { $env:INJECT_JS = $Extra } else { Remove-Item Env:INJECT_JS -ErrorAction SilentlyContinue }
if ($Fill -gt 0) { $env:FILL = "$Fill" } else { Remove-Item Env:FILL -ErrorAction SilentlyContinue }
$busy = @(); $late = @(); $drop = @(); $worst = @()
for ($i = 0; $i -lt $Runs; $i++) {
  $out = node "$sp\measure.mjs" $Throttle $Taps $Secs | Out-String
  if ($out -match '"mainThreadBusyPct":\s*([\d.]+)') { $busy += [double]$Matches[1] }
  if ($out -match 'worst tick late (\d+)ms.*?late steps (\d+)\s+dropped (\d+)') { $worst += [int]$Matches[1]; $late += [int]$Matches[2]; $drop += [int]$Matches[3] }
}
Remove-Item Env:INJECT_CSS -ErrorAction SilentlyContinue; Remove-Item Env:FILL -ErrorAction SilentlyContinue
"{0,-34} busy%[{1}]  worstLate[{2}]  late[{3}]  dropped[{4}]" -f $Label, ($busy -join ','), ($worst -join ','), ($late -join ','), ($drop -join ',')
