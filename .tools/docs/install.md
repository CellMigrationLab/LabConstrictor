# Install an app

Installing takes about 6-8 minutes and you only do it once. Download the installer for your system from the app's page in the [App Centre](https://labconstrictor.cellmig.org/apps/) (or from the app's GitHub release) and follow the steps for your system.

> **Check where it comes from.** The installers are not code-signed yet, so your system will warn you. Download only from the app's own GitHub release (the address starts with `https://github.com/` followed by the app's owner and repository, as shown on the app's page), and run it only if you trust that owner. A listing in the App Centre checks that the files come from the app's repository; it is not a security audit.

> A command prompt window opens during installation on Windows; this is normal, do not close it.

## Windows

1. Download the `.exe` file and double-click it.
2. If Windows shows "Windows protected your PC", click "More info" and then "Run anyway". The installers are not code-signed yet.

   ![Windows protected your PC: click More info, then Run anyway](https://github.com/CellMigrationLab/LabConstrictor/blob/doc_source/Windows_Protected_your_PC.png)

3. Follow the on-screen prompts. Launch the app from the Start Menu or your desktop.

## macOS

1. Choose your file: open the Apple menu, then About This Mac. If the Chip or Processor says Intel, download the Intel installer; if it says M1, M2 or similar, download the Apple Silicon one.
2. Double-click the `.pkg` file. If macOS refuses to open it, go to System Settings, Privacy & Security, scroll down to the message about the package and click "Open Anyway" (it appears only after you tried to open the file once). If you do not see it, try opening the file again, then check this page again.
3. Follow the prompts (we recommend "Install only for me"). Launch the app from your Applications folder.

## Linux

1. Download the `.sh` file.
2. Open a terminal in the download folder and run `bash` followed by the name of the file you downloaded, for example: `bash MyApp-0.1.0-Linux-x86_64.sh`
3. Follow the prompts, then launch the app from your applications menu.

## Next

Open the app and start working: [Use notebooks after installation](notebook_usage.md). If something goes wrong, see [Troubleshooting an installed app](troubleshooting_installed_app.md).
