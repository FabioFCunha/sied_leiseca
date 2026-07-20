import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('187.127.45.148', username='root', password='eeX1d3Vnbp#rbN&)')

files_to_upload = [
    ("backend/apps/schedules/views.py", "/root/agenda-educacao/backend/apps/schedules/views.py"),
]

sftp = client.open_sftp()
for local, remote in files_to_upload:
    print(f"Uploading {local} to {remote}...")
    sftp.put(local, remote)
sftp.close()

print("Rebuilding...")
stdin, stdout, stderr = client.exec_command('cd /root/agenda-educacao && docker compose build backend && docker compose up -d backend')

# avoid decode error by writing bytes or ignoring
print("Done!")
