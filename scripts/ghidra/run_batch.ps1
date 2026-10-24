# Run a task file against the persistent Ghidra project (H3). One Ghidra process at a time.
# usage: powershell -File run_batch.ps1 TASK_FILE OUT_FILE
param([Parameter(Mandatory)][string]$Tasks, [Parameter(Mandatory)][string]$Out)
$ghidra = 'C:\Users\zackp\Documents\Code stuff\tools\ghidra_12.1.4_PUBLIC'
$env:JAVA_HOME = 'C:\Users\zackp\Documents\Code stuff\tools\jdk\jdk-21.0.12.1+1'
$project = 'C:\Users\zackp\Documents\Code stuff\tools\ghidra_projects\DayZ'
& "$ghidra\support\analyzeHeadless.bat" $project DayZ -process DayZ_x64.exe -noanalysis -readOnly `
    -scriptPath $PSScriptRoot -postScript BatchDecompile.java (Resolve-Path $Tasks).Path $Out
