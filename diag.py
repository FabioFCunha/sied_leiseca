import paramiko

host = '187.127.45.148'
user = 'root'
password = 'eeX1d3Vnbp#rbN&)'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(host, username=user, password=password, timeout=10)
    print('--- 1. VPS INFO ---')
    stdin, stdout, stderr = client.exec_command('uptime; echo "--- CPU ---"; top -bn1 | head -n 5; echo "--- MEMORY ---"; free -h; echo "--- DISK ---"; df -h /')
    print(stdout.read().decode())
    
    print('--- 2. DOCKER PS ---')
    stdin, stdout, stderr = client.exec_command('docker ps -a')
    print(stdout.read().decode())

    print('--- 3. LOGS PROXY ---')
    stdin, stdout, stderr = client.exec_command('docker logs --tail 50 sied_proxy')
    print(stdout.read().decode())
    print(stderr.read().decode())

    print('--- 3. LOGS BACKEND ---')
    stdin, stdout, stderr = client.exec_command('docker logs --tail 50 sied_backend')
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    print('--- 3. LOGS FRONTEND ---')
    stdin, stdout, stderr = client.exec_command('docker logs --tail 50 sied_frontend')
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    print('--- 3. LOGS DB ---')
    stdin, stdout, stderr = client.exec_command('docker logs --tail 20 sied_db')
    print(stdout.read().decode())
    print(stderr.read().decode())

    print('--- 4. NGINX & SSL ---')
    stdin, stdout, stderr = client.exec_command('ls -l /etc/letsencrypt/live/sied-leiseca.online/ || echo "NO SSL CERT DIR"')
    print(stdout.read().decode())
    print(stderr.read().decode())

    print('--- 5. REDE LOCAL ---')
    stdin, stdout, stderr = client.exec_command('curl -s -I http://localhost')
    print(stdout.read().decode())
    
    stdin, stdout, stderr = client.exec_command('curl -s -I http://localhost/healthz')
    print(stdout.read().decode())

    client.close()
except Exception as e:
    print('SSH ERROR:', e)
