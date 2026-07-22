import paramiko
import os

host = '187.127.45.148'
user = 'root'
password = 'eeX1d3Vnbp#rbN&)'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=10)

sftp = client.open_sftp()
local_path = "frontend/nginx.conf"
remote_path = "/root/agenda-educacao/frontend/nginx.conf"
print(f"Uploading {local_path} to {remote_path}...")
sftp.put(local_path, remote_path)
sftp.close()

print("Rebuilding frontend container on VPS...")
stdin, stdout, stderr = client.exec_command("cd /root/agenda-educacao && docker compose build frontend && docker compose up -d frontend")
exit_status = stdout.channel.recv_exit_status()

print("STDOUT:", stdout.read().decode('utf-8'))
print("STDERR:", stderr.read().decode('utf-8'))
print(f"Done with exit status {exit_status}")
client.close()
