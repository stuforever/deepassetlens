$checks = @(
    @{name='frontend 3000'; url='http://127.0.0.1:3000'},
    @{name='backend 8100 docs'; url='http://127.0.0.1:8100/docs'},
    @{name='backend 8100 health'; url='http://127.0.0.1:8100/api/health'},
    @{name='qdrant 6333'; url='http://127.0.0.1:6333/healthz'},
    @{name='langgraph 17206 assistants'; url='http://127.0.0.1:17206/assistants'},
    @{name='langgraph 17206 ok'; url='http://127.0.0.1:17206/ok'}
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
