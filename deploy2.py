import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('187.127.45.148', username='root', password='eeX1d3Vnbp#rbN&)')

files_to_upload = [
    ("frontend/public/version.json", "/root/agenda-educacao/frontend/public/version.json"),
]

sftp = client.open_sftp()
for local, remote in files_to_upload:
    print(f"Uploading {local} to {remote}...")
    sftp.put(local, remote)
sftp.close()

print("Rebuilding...")
stdin, stdout, stderr = client.exec_command('cd /root/agenda-educacao && docker compose build --no-cache frontend && docker compose up -d frontend')

print("Done!")
