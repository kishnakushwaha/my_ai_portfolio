import subprocess
import glob
import os

found_helpers = glob.glob("/opt/homebrew/Cellar/git/*/libexec/git-core/git-credential-osxkeychain")
print(f"Found helpers: {found_helpers}")

if found_helpers:
    helper = found_helpers[-1]
    print(f"Testing helper: {helper}")
    
    input_data = "protocol=https\nhost=github.com\nusername=kishnakushwaha91-afk\n"
    
    try:
        res = subprocess.run([helper, "get"], input=input_data, text=True, capture_output=True, check=True)
        print("SUCCESS! Credential retrieved.")
        print(f"Output: {res.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"FAIL with code {e.returncode}")
        print(f"Stderr: {e.stderr}")
else:
    print("No helper found via glob.")
