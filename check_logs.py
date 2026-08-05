import paramiko

host = '187.127.45.148'
user = 'root'
password = 'eeX1d3Vnbp#rbN&)'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=10)

_, stdout, _ = client.exec_command('docker logs sied_backend --tail 500 | grep 403')
print('OUT:', stdout.read().decode('utf-8', errors='ignore'))
client.close()
