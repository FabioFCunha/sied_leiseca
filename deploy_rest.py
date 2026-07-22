import paramiko
import os

host = '187.127.45.148'
user = 'root'
password = 'eeX1d3Vnbp#rbN&)'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password, timeout=10)
sftp = client.open_sftp()

files_to_upload = [
    ("frontend/src/utils/reportPreview.js", "/root/agenda-educacao/frontend/src/utils/reportPreview.js"),
    ("frontend/src/utils/educationGoals.js", "/root/agenda-educacao/frontend/src/utils/educationGoals.js"),
    ("frontend/src/utils/streetActionTypes.js", "/root/agenda-educacao/frontend/src/utils/streetActionTypes.js"),
    ("frontend/src/pages/StatisticsPage.jsx", "/root/agenda-educacao/frontend/src/pages/StatisticsPage.jsx")
]

for local_path, remote_path in files_to_upload:
    print(f"Uploading {local_path}...")
    sftp.put(local_path, remote_path)

sftp.close()

print("Rebuilding frontend container on VPS...")
stdin, stdout, stderr = client.exec_command("cd /root/agenda-educacao && docker compose build frontend && docker compose up -d frontend")
exit_status = stdout.channel.recv_exit_status()
print(f"Done with exit status {exit_status}")
client.close()
