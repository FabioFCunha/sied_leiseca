import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('187.127.45.148', username='root', password='eeX1d3Vnbp#rbN&)')
stdin, stdout, stderr = client.exec_command('grep -r "streetActionTypeOptions.map" /root/agenda-educacao/frontend/src/pages/TechnicalReportsPage.jsx')
print(stdout.read().decode('utf-8'))
