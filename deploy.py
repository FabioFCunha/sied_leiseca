import paramiko
import os
from paramiko import SSHClient, AutoAddPolicy

def deploy():
    host = "187.127.45.148"
    user = "root"
    password = "eeX1d3Vnbp#rbN&)"
    
    files_to_upload = [
        ("frontend/src/pages/TechnicalReportsPage.jsx", "/root/agenda-educacao/frontend/src/pages/TechnicalReportsPage.jsx"),
        ("frontend/src/pages/UsersPage.jsx", "/root/agenda-educacao/frontend/src/pages/UsersPage.jsx"),
        ("backend/apps/schedules/views.py", "/root/agenda-educacao/backend/apps/schedules/views.py"),
        ("backend/apps/schedules/serializers.py", "/root/agenda-educacao/backend/apps/schedules/serializers.py")
    ]
    
    print("Connecting to VPS...")
    try:
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())
        client.connect(host, username=user, password=password, timeout=10)
        sftp = client.open_sftp()
        
        for local_path, remote_path in files_to_upload:
            print(f"Uploading {local_path} to {remote_path}...")
            sftp.put(local_path, remote_path)
            
        sftp.close()
        print("Upload complete!")
        
        # Now run the docker commands
        print("Rebuilding containers on VPS...")
        stdin, stdout, stderr = client.exec_command("cd /root/agenda-educacao && docker compose build frontend backend && docker compose up -d")
        
        # We need to wait for it to finish and get output
        exit_status = stdout.channel.recv_exit_status()
        print("STDOUT:", stdout.read().decode('utf-8', errors='replace'))
        print("STDERR:", stderr.read().decode('utf-8', errors='replace'))
        
        client.close()
        print(f"Deployment finished with status {exit_status}")
    except Exception as e:
        print("Error during deploy:", e)

if __name__ == "__main__":
    deploy()
