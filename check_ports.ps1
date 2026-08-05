$ports = @(3000,6333,7474,7687,8100,2024,17206)
foreach ($p in $ports) {
    $c = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    if ($c) {
        foreach ($conn in $c) {
            $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
            $name = if ($proc) { $proc.ProcessName } else { '<dead>' }
            Write-Output ("  :{0,-6} LISTEN  PID={1,-6}  {2}" -f $p, $conn.OwningProcess, $name)
        }
    } else {
        Write-Output ("  :{0,-6} DOWN" -f $p)
    }
}
