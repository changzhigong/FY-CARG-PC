@echo off
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
$urls = Get-Content 'urls.txt'; ^
foreach ($url in $urls) { ^
    $number = ($url -split '/')[4];^
    echo 提取的数字是：$number}
pause
