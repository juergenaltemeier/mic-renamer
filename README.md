# Mic Renamer

A cross-platform desktop tool to rename photos and videos using project numbers, tag codes and optional suffixes. The UI is built with PySide6.

## Setup

1. Install Python 3.10 or newer.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # on Windows use .\venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Start the application:
   ```bash
   python -m mic_renamer
   ```

Configuration files are stored in a user specific directory (for example
`~/.config/mic_renamer` on Linux). Set the `RENAMER_CONFIG_DIR` environment
variable if you want them somewhere else, e.g. on your `D:` drive. Defaults
ship with the project in `mic_renamer/config/defaults.yaml` and are merged with
your configuration on start. A `tags.json` file is copied to the configuration
folder the first time the program runs so you can adapt it to your needs. The
application also remembers the last used project number.

Tag usage statistics are written to ``tag_usage.json`` in the same
configuration directory. You can discover the full path programmatically:

```python
from mic_renamer.logic.tag_usage import get_usage_path
print(get_usage_path())
```

## Running Tests

The unit tests depend on **PySide6** and system OpenGL libraries. On many
Linux distributions the latter are provided by ``libegl1``. Without these
packages the test suite will fail to initialize the Qt platform plugin.

Install PySide6 in your virtual environment and ensure the system OpenGL
libraries are available:

```bash
pip install PySide6
# on Debian/Ubuntu
sudo apt-get install libegl1
```

Headless environments may require additional setup, such as a virtual display
server (Xvfb) or GPU drivers, to run the tests successfully.

## Building a Standalone Executable

The repository contains three spec files for [PyInstaller](https://pyinstaller.org/):

* ``mic_renamer.spec`` – builds a folder style distribution in ``dist/mic-renamer``
  The resulting ``mic-renamer.exe`` runs without opening a console and includes
  the icon if ``favicon.png``/``favicon.ico`` are present.
* ``mic_renamer_onefile.spec`` – like above but produces a single file executable.
* ``mic-renamer.spec`` – a minimal spec kept for reference. You normally do not
  need this one.

Use one of the first two spec files from the repository root:

```bash
pip install pyinstaller

# folder build
pyinstaller mic_renamer.spec

# single file build
pyinstaller mic_renamer_onefile.spec

```

The resulting build directory is written to ``dist/mic-renamer``. If you prefer
a single-file executable you can call PyInstaller directly on the entry module
and pass ``--onefile``.

## FFmpeg Dependency for Video Thumbnails

To provide static thumbnails for video formats not supported by Qt Multimedia (such as AV1), mic-renamer invokes the FFmpeg CLI to extract the first frame. Ensure that:
1. An `ffmpeg` executable is available on the system `PATH`, or
2. You bundle a platform-specific FFmpeg binary in `mic_renamer/resources/ffmpeg/<platform>/ffmpeg` (or `ffmpeg.exe` on Windows).
 
With FFmpeg accessible, unsupported videos will display a still-frame preview instead of a black screen.

### Custom Executable Icon

To give the application and generated executable a custom icon, create your own
``favicon.png`` and place it inside the ``mic_renamer`` package directory.
Optionally create a matching ``favicon.ico`` next to the spec file. You can
convert any PNG image to ICO using Pillow:

```bash
from PIL import Image
Image.open("my_icon.png").save("favicon.png")
Image.open("my_icon.png").save("favicon.ico")
```

After placing the icons, build the executable. The spec files automatically
pick up ``favicon.ico`` when present. You can also pass ``--icon`` manually:

```bash
pyinstaller --icon favicon.ico mic_renamer.spec
```

If you run PyInstaller directly on the entry module, pass ``--noconsole`` to
avoid an extra terminal window:

```bash
pyinstaller --noconsole --icon favicon.ico mic_renamer/__main__.py
```

Some antivirus tools flag UPX-compressed executables. If this occurs, disable
compression by passing ``--noupx`` or editing the spec files to set
``upx=False``.

## Code Signing for Internal Distribution (Windows)

To prevent Windows from displaying "dangerous" or "unrecognized app" warnings when running the `MIC-ImageRenamer.exe` executable on internal machines, you can digitally sign the executable with a self-signed code signing certificate. This process involves generating a certificate, exporting it, signing the executable, and then installing the certificate on target machines.

### Prerequisites

*   **Windows SDK:** You need `signtool.exe`, which is part of the Windows SDK. Ensure it's installed. During installation, select "Windows SDK Signing Tools for Desktop Apps". The tool is typically found at `C:\Program Files (x86)\Windows Kits\10\bin\<Windows SDK Version>\x64\signtool.exe`.
*   **PowerShell:** Used for certificate management and running scripts.

### Step 1: Generate a Self-Signed Code Signing Certificate

Open a **regular (non-admin) PowerShell** window and run the following command. This creates a new self-signed certificate valid for 10 years and places it in your personal certificate store.

```powershell
New-SelfSignedCertificate -Subject "CN=Mic-Renamer Internal" -CertStoreLocation "Cert:\CurrentUser\My" -Type CodeSigning -KeyUsage DigitalSignature -NotAfter (Get-Date).AddYears(10)
```

Make a note of the `Thumbprint` that is displayed after running this command. You will need it for the next step.

### Step 2: Export the Certificate to a .pfx file

You need to export the certificate (including its private key) to a `.pfx` file. This file will be used to sign your executable.

1.  **Open Certificate Manager:**
    *   Press `Win + R` to open the Run dialog.
    *   Type `certmgr.msc` and press Enter.
2.  **Navigate to Your Certificate:**
    *   In the Certificate Manager window, expand `Personal` -> `Certificates`.
    *   You should see your newly created certificate: `Mic-Renamer Internal`.
3.  **Export the Certificate:**
    *   Right-click on the `Mic-Renamer Internal` certificate.
    *   Select `All Tasks` -> `Export...`.
    *   The Certificate Export Wizard will open. Click `Next`.
    *   Select `Yes, export the private key` and click `Next`. (This is crucial for code signing).
    *   On the Export File Format screen, ensure `Personal Information Exchange - PKCS #12 (.PFX)` is selected.
    *   Check `Include all certificates in the certification path if possible`.
    *   Check `Export all extended properties`.
    *   Click `Next`.
    *   **Security:** Check `Password`. Enter a strong password (e.g., `MG3dVFCgTNenFQhF9yWz`) and confirm it. This password protects the private key. Click `Next`.
    *   **File to Export:** Click `Browse...`. Navigate to your project directory (e.g., `D:\mic-renamer\`) and save the file as `MicRenamerInternal.pfx`. Click `Save`.
    *   Click `Next`.
    *   Click `Finish`. You should see a message "The export was successful."

### Step 3: Sign the Executable

Now, use `signtool.exe` to sign your `MIC-ImageRenamer.exe` executable. Replace `C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe` with the actual path to your `signtool.exe` if it's different.

Open a **PowerShell** or **Command Prompt** window, navigate to the directory containing `signtool.exe` (or use its full path), and run:

```powershell
"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe" sign /f "D:\mic-renamer\MicRenamerInternal.pfx" /p "MG3dVFCgTNenFQhF9yWz" /fd sha256 /tr http://timestamp.digicert.com /td sha256 /v "D:\mic-renamer\dist\mic-renamer\MIC-ImageRenamer.exe"
```

*   `/f`: Specifies the `.pfx` certificate file.
*   `/p`: Specifies the password for the `.pfx` file.
*   `/fd sha256`: Specifies the file digest algorithm (SHA256).
*   `/tr http://timestamp.digicert.com`: Specifies a timestamp server URL. This ensures the signature remains valid even after the certificate expires.
*   `/td sha256`: Specifies the timestamp digest algorithm (SHA256).
*   `/v`: Enables verbose output.

After execution, you should see output indicating successful signing. You can verify the signature by right-clicking on the `MIC-ImageRenamer.exe` file, selecting `Properties`, and checking for a `Digital Signatures` tab.

### Step 4: Install the Certificate on Target Machines

To prevent warnings on other internal machines, you need to install the `MicRenamerInternal.pfx` certificate into their "Trusted Root Certification Authorities" store.

Save the following content as `install_cert.ps1` in the same directory as your `MicRenamerInternal.pfx` file:

```powershell
# install_cert.ps1
# This script installs the MicRenamerInternal.pfx certificate into the Trusted Root Certification Authorities store.

# Define variables
$pfxFilePath = Join-Path $PSScriptRoot "MicRenamerInternal.pfx"
$pfxPassword = "MG3dVFCgTNenFQhF9yWz" # IMPORTANT: Replace with your actual password

# Check if the PFX file exists
if (-not (Test-Path $pfxFilePath)) {
    Write-Error "Certificate file not found: $pfxFilePath"
    exit 1
}

# Attempt to install the certificate
try {
    Write-Host "Installing certificate from $pfxFilePath..."

    # Import the PFX into the Personal store first (required for private key)
    Import-PfxCertificate -FilePath $pfxFilePath -CertStoreLocation Cert:\CurrentUser\My -Password (ConvertTo-SecureString -String $pfxPassword -AsPlainText -Force) -Exportable

    # Get the certificate from the Personal store
    $cert = Get-ChildItem -Path Cert:\CurrentUser\My | Where-Object {$_.Subject -eq "CN=Mic-Renamer Internal"} | Select-Object -First 1

    if ($cert) {
        Write-Host "Certificate found in Personal store. Moving to Trusted Root Certification Authorities..."
        
        # Move the certificate to the Trusted Root Certification Authorities store
        $cert | Move-Item -Destination Cert:\LocalMachine\Root

        Write-Host "Certificate installed successfully into Trusted Root Certification Authorities."
    } else {
        Write-Error "Failed to find certificate 'CN=Mic-Renamer Internal' after importing PFX."
        exit 1
    }
} catch {
    Write-Error "An error occurred during certificate installation: $($_.Exception.Message)"
    exit 1
}

Write-Host "Installation script finished."
```

**How to use `install_cert.ps1`:**

1.  **Copy** `MicRenamerInternal.pfx` and `install_cert.ps1` to the target machine (e.g., to a temporary folder like `C:\Temp\MicRenamerCert\`).
2.  **Open PowerShell as Administrator:**
    *   Search for "PowerShell" in the Start Menu.
    *   Right-click on "Windows PowerShell" and select "Run as administrator".
3.  **Navigate to the directory** where you saved the files:
    ```powershell
    cd C:\Temp\MicRenamerCert\
    ```
4.  **Run the script:**
    ```powershell
    .\install_cert.ps1
    ```

The script will execute, and if successful, the certificate will be installed. After this, any applications signed with this certificate should no longer trigger the "dangerous" warning on that machine.