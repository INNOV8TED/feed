import os
import ftplib

FTP_HOST = "ftp.in-no-v8.com"
FTP_USER = "innov8co"
FTP_PASS = "%odn*fr*l4a7$e"
REMOTE_DIR = "/in-no-v8.world"

def upload_file(ftp, local_path, remote_path):
    with open(local_path, 'rb') as f:
        print(f"Uploading {local_path} -> {remote_path}...")
        ftp.storbinary(f'STOR {remote_path}', f)

def deploy():
    print(f"Connecting SECURELY to FTP Server: {FTP_HOST}...")
    ftp = ftplib.FTP_FTP_TLS if hasattr(ftplib, 'FTP_FTP_TLS') else ftplib.FTP_TLS
    ftp_conn = ftp(FTP_HOST, timeout=15)
    ftp_conn.login(FTP_USER, FTP_PASS)
    ftp_conn.prot_p()
    print("Connected successfully.")
    
    # Create the remote directory if it doesn't exist
    try:
        ftp_conn.mkd(REMOTE_DIR)
        print(f"Created remote directory: {REMOTE_DIR}")
    except ftplib.error_perm:
        print(f"Remote directory {REMOTE_DIR} already exists.")
        
    # Upload world/index.html as /in-no-v8.world/index.html
    upload_file(ftp_conn, 'world/index.html', f'{REMOTE_DIR}/index.html')
    
    # Upload world/flap.mp3 as /in-no-v8.world/flap.mp3
    if os.path.exists('world/flap.mp3'):
        upload_file(ftp_conn, 'world/flap.mp3', f'{REMOTE_DIR}/flap.mp3')
    else:
        print("WARNING: world/flap.mp3 not found!")
        
    # Upload world/favicon.png or fallback to root favicon.png
    if os.path.exists('world/favicon.png'):
        upload_file(ftp_conn, 'world/favicon.png', f'{REMOTE_DIR}/favicon.png')
    elif os.path.exists('favicon.png'):
        upload_file(ftp_conn, 'favicon.png', f'{REMOTE_DIR}/favicon.png')

    # Upload world/sample.png if it exists
    if os.path.exists('world/sample.png'):
        upload_file(ftp_conn, 'world/sample.png', f'{REMOTE_DIR}/sample.png')
        
    ftp_conn.quit()
    print("\nDeploy complete! The Split-Flap board is now live at https://in-no-v8.world/")

if __name__ == "__main__":
    deploy()
