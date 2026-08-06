$checks = @(
    @{name='frontend 23000'; url='http://127.0.0.1:23000'},
    @{name='backend 28000 openapi'; url='http://127.0.0.1:28000/openapi.json'},
    @{name='backend 28000 concepts'; url='http://127.0.0.1:28000/api/v1/concepts'},
    @{name='qdrant 6333'; url='http://127.0.0.1:6333/healthz'},
    @{name='langgraph 2024 assistants'; url='http://127.0.0.1:2024/assistants'},
    @{name='langgraph 2024 ok'; url='http://127.0.0.1:2024/ok'}
)
foreach ($c in $checks) {
    try {
        $r = Invoke-WebRequest -Uri $c.url -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        Write-Output ("  [{0,-22}] {1,-50}  HTTP {2}" -f $c.name, $c.url, $r.StatusCode)
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if ($code) {
            Write-Output ("  [{0,-22}] {1,-50}  HTTP {2}" -f $c.name, $c.url, $code)
        } else {
            Write-Output ("  [{0,-22}] {1,-50}  FAIL  {2}" -f $c.name, $c.url, $_.Exception.Message)
        }
    }
}
