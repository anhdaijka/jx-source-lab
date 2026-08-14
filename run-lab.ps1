param([Parameter(Position=0)][string]$Command="inventory",[Parameter(ValueFromRemainingArguments=$true)][string[]]$Rest)
$ErrorActionPreference="Stop"
python "$PSScriptRoot\scripts\jxlab.py" $Command @Rest
