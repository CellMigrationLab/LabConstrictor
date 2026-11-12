# Troubleshooting repository setup

Problems with your repository on GitHub. For problems with an installed app on your computer, see [Troubleshooting an installed app](troubleshooting_installed_app.md).

## Synchronisation is failing on GitHub Actions

The **Sync with Template Repository** workflow needs the encrypted repository secret `LABCONSTRICTOR_SYNC_TOKEN` because template migrations can update files in `.github/workflows/`. Follow the [automatic template synchronization guide](template_synchronization.md) for the complete beginner-friendly setup.

### The synchronization token is missing

Create the token and save it under **Settings → Secrets and variables → Actions** with this exact name:

```text
LABCONSTRICTOR_SYNC_TOKEN
```

### GitHub refuses to update a workflow file

If the error says GitHub is refusing to create or update a workflow without `workflows` permission, ensure the token has all of these repository permissions:

- **Contents:** Read and write
- **Pull requests:** Read and write
- **Workflows:** Read and write

Repositories created before template version `0.1.12` also need the one-time workflow edit described in the synchronization guide so the existing workflow starts using the secret.

### Bad credentials or authentication failed

The token may have expired or been revoked. Create a replacement token and update the existing `LABCONSTRICTOR_SYNC_TOKEN` secret.

---

<div align="center">

[← Previous](workflow_status.md) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
[🏠 Home](README.md) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
[Next →](personal_access_token.md)


</div>

## The release stops at "check_placeholders.py"

The release workflow checks, before it builds the installers, that no template placeholder (`PROJECT_NAME`, `PYTHON_PROJ_NAME`, `UNDERSCORED_PROJECT_NAME`, ...) is left in a file the installer ships. An installer built with one would fail on the users' computers (for example `No module named 'PYTHON_PROJ_NAME'` at the end of the installation).

The log of the failed step lists each file and line. Replace the placeholder there with your app's value: `PYTHON_PROJ_NAME` is the Python package of the app (usually its folder in `src/`), `PROJECT_NAME` the app name. For `app/menuinst/Welcome.ipynb`, edit `.tools/templates/Welcome_template.ipynb` instead: the Welcome notebook is made from it at every release. Commit, then publish the release again. See [migration_0_1_23.md](migration_0_1_23.md).
