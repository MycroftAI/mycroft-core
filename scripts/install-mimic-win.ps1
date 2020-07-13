$url = "https://github.com/MycroftAI/mimic1/releases/latest/download/mimic_windows_amd64.zip"
$tmp = New-TemporaryFile | Rename-Item -NewName {$_ -replace 'tmp$', 'zip'} -PassThru
#download
Invoke-WebRequest -OutFile $tmp $url
#exract to same folder 
$tmp | Expand-Archive -DestinationPath mimic/bin -Force
# remove temporary file
$tmp | Remove-Item