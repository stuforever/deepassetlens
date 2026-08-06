$ports = @(23000,28000,33066,5432,11200,9030,18030,6333,6334,7474,7687,2024)
$names = @{
    23000 = 'frontend'
    28000 = 'backend'
    33066 = 'MySQL'
    5432  = 'PostgreSQL'
    11200 = 'Elasticsearch'
    9030  = 'Doris FE'
    18030 = 'Doris FE HTTP'
    6333  = 'Qdrant REST'
    6334  = 'Qdrant gRPC'
    7474  = 'Neo4j Browser'
    7687  = 'Neo4j Bolt'
    2024  = 'LangGraph'
}
foreach ($p in $ports) {
    $c = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    $label = $names[$p]
    if ($c) {
        foreach ($conn in $c) {
            $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
            $name = if ($proc) { $proc.ProcessName } else { '<dead>' }
            Write-Output ("  :{0,-6} {1,-16} LISTEN  PID={2,-6}  {3}" -f $p, $label, $conn.OwningProcess, $name)
        }
    } else {
        Write-Output ("  :{0,-6} {1,-16} DOWN" -f $p, $label)
    }
}