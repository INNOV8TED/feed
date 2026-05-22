import ftplib
import os

# Server Configuration
FTP_HOST = "ftp.in-no-v8.com"
FTP_USER = "innov8co"
FTP_PASS = "%odn*fr*l4a7$e"
REMOTE_PATH = "/in-no-v8.world/" # Matches your cPanel Addon Domain folder

def deploy():
    print(f">>> Connecting SECURELY to {FTP_HOST}...")
    try:
        # Use FTP_TLS for secure connection
        with ftplib.FTP_TLS(FTP_HOST) as ftp:
            ftp.login(user=FTP_USER, passwd=FTP_PASS)
            ftp.prot_p() # Switch to secure data channel (REQUIRED by many servers)
            print(">>> Secure Login Successful.")
            
            # Change to target directory
            ftp.cwd(REMOTE_PATH)
            
            files_to_upload = ["index.html", "flap.mp3", "favicon.png", "sample.png"]
            
            for filename in files_to_upload:
                if os.path.exists(filename):
                    print(f">>> Uploading {filename}...")
                    with open(filename, "rb") as f:
                        ftp.storbinary(f"STOR {filename}", f)
                else:
                    print(f">>> [SKIP] {filename} not found locally.")
            
            print("\n>>> DEPLOYMENT COMPLETE! Live at in-no-v8.world")
            
    except Exception as e:
        print(f">>> [ERROR] {str(e)}")

if __name__ == "__main__":
    deploy()
