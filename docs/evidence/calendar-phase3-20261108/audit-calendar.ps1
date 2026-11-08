$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$prior = Join-Path (Split-Path $root) 'official-history-phase2'
$targets = @('2017-02-18','2017-06-03','2017-09-30','2018-03-31','2018-12-22','2019-09-09','2021-04-06','2025-08-01','2026-10-23')
$months = $targets | ForEach-Object { $_.Substring(0,7) } | Select-Object -Unique
$utf8 = New-Object System.Text.UTF8Encoding($false)
$sources = @()
foreach ($month in $months) {
    $path = Join-Path $root "twse-market-$month.json"
    $url = 'https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK?date=' + $month.Replace('-','') + '01&response=json'
    if (!(Test-Path -LiteralPath $path)) {
        Start-Sleep -Seconds 3
        # No retries or alternate endpoint on access denial. Keep successful cache.
        Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $path
    }
    $payload = Get-Content -Raw -Encoding UTF8 -LiteralPath $path | ConvertFrom-Json
    if ($payload.stat -ne 'OK' -or $payload.date -ne ($month.Replace('-','')+'01') -or $payload.fields[0] -ne '日期' -or $payload.fields[1] -ne '成交股數') { throw "Unexpected market schema/month: $month" }
    $sources += [ordered]@{month=$month;url=$url;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower();fields=$payload.fields;notes=$payload.notes}
}
$rows = @()
$inputs = @()
foreach ($symbol in @('2330.TW','3105.TWO')) {
    $dir = if ($symbol -eq '2330.TW') {'2330-complete'} else {'3105-complete'}
    $dailyPath = Join-Path $prior "$dir\${symbol}_official_daily.csv"
    $providerPath = Join-Path $prior "$dir\${symbol}_provider_original.csv"
    $inputs += [ordered]@{symbol=$symbol;official_sha256=(Get-FileHash -LiteralPath $dailyPath -Algorithm SHA256).Hash.ToLower();provider_sha256=(Get-FileHash -LiteralPath $providerPath -Algorithm SHA256).Hash.ToLower()}
    $official = Import-Csv -LiteralPath $dailyPath
    $provider = Import-Csv -LiteralPath $providerPath
    foreach ($date in $targets) {
        $p = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $root ('twse-market-'+$date.Substring(0,7)+'.json')) | ConvertFrom-Json
        $d = [datetime]::ParseExact($date,'yyyy-MM-dd',[cultureinfo]::InvariantCulture)
        $roc = '{0}/{1:00}/{2:00}' -f ($d.Year-1911),$d.Month,$d.Day
        $market = @($p.data | Where-Object { $_[0] -eq $roc })
        $o = @($official | Where-Object { $_.date -eq $date -or $_.Date -eq $date })
        $v = @($provider | Where-Object { $_.Date -eq $date })
        if ($market.Count -gt 1 -or $o.Count -gt 1 -or $v.Count -gt 1) { throw "Duplicate date $symbol $date" }
        $rows += [ordered]@{symbol=$symbol;date=$date;weekday=$d.DayOfWeek.ToString();twse_market_row_present=($market.Count -eq 1);official_stock_row_present=($o.Count -eq 1);provider_row_present=($v.Count -eq 1);classification= $(if ($market.Count -eq 1 -and $o.Count -eq 1 -and $v.Count -eq 0) {'provider_missing_observed_session'} elseif ($date -eq '2026-10-23' -and $market.Count -eq 0 -and $o.Count -eq 0 -and $v.Count -eq 1) {'provider_extra_on_twse_announced_closure'} else {'unconfirmed'});scope_note=$(if ($symbol -eq '3105.TWO') {'TWSE market evidence corroborates date only; OTC-specific closure announcement not yet independently fetched.'} else {'TWSE market plus stock-month comparison; not full calendar certification.'})}
    }
}
$report = [ordered]@{created_utc=[datetime]::UtcNow.ToString('o');scope='Two stocks, nine predefined difference dates; not whole-market or full-calendar audit';production_ready=$false;applied_to_data=$false;full_calendar_certified=$false;input_fingerprints=$inputs;closure_evidence=[ordered]@{date='2026-10-23';market='TWSE';publication_date='2026-10-22';url='https://investoredu.twse.com.tw/FileSystem/FileUpload/c91c7dff-afb0-42cc-9949-9f072bece31d.pdf';verification='Official PDF independently read via web browser tool; typhoon full-day closure. OTC-specific notice still pending.'};sources=$sources;rows=$rows}
[IO.File]::WriteAllText((Join-Path $root 'calendar-audit.json'),($report | ConvertTo-Json -Depth 12),$utf8)
$rows | ForEach-Object {[pscustomobject]$_} | Export-Csv -NoTypeInformation -Encoding UTF8 -LiteralPath (Join-Path $root 'calendar-audit.csv')
Write-Output ($rows | ForEach-Object {[pscustomobject]$_} | Group-Object classification | Select-Object Name,Count | ConvertTo-Json)
