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
