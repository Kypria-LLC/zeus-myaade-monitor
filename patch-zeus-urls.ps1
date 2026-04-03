$file = "D:\Projects\zeus-myaade-monitor\myaade_monitor_zeus.py"
$c = [System.IO.File]::ReadAllText($file)
$c = $c.Replace('    MYAADE_PROTOCOLS: str = "https://www1.aade.gr/taxisnet/protocols"', "    MYAADE_INBOX: str = ""https://www1.aade.gr/taxisnet/mymessages/protected/inbox.htm""`n    MYAADE_VIEW_MESSAGE: str = ""https://www1.aade.gr/taxisnet/mymessages/protected/viewMessage.htm""`n    MYAADE_APPLICATIONS: str = ""https://www1.aade.gr/taxisnet/mytaxisnet/protected/applications.htm""")
$c = $c.Replace('self.driver.get(config.MYAADE_PROTOCOLS)', 'self.driver.get(config.MYAADE_INBOX)')
$c = $c.Replace('input[type=''text''], input[name*=''protocol''], #protocolSearch', '#searchResults td a, #searchResults td')
$c = $c.Replace('button[type=''submit''], .search-btn, #searchBtn', '#searchResults')
$c = $c.Replace('.status, .protocol-status, td, .result-text, .response', '#searchResults td, .message-body, .msg-content')
$c = $c.Replace('logger.warning("Protocol search UI not found, reading page directly")', 'logger.warning("Inbox table not found, reading page directly")')
[System.IO.File]::WriteAllText($file, $c)
Write-Host "PATCHED OK" -ForegroundColor Green
