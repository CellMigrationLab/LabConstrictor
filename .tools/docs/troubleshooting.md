# Troubleshooting

## App still appears in the Windows Installed apps list after uninstalling

On Windows, it may happen that, after uninstalling the app from `Settings > Apps > Installed apps` as explained in the [uninstalling guide](./download_executable.md), the app still appears in the list and does not allow you to uninstall it again, showing a message like:

![Uninstall error message](https://github.com/CellMigrationLab/LabConstrictor/blob/doc_source/troubleshooting/Not_Uninstall.png)

The solution is to go to the Control Panel and uninstall it from there. To do this:

1. Open the Control Panel. You can search for it in the Windows search bar.
2. Go to `Programs > Programs and Features`.
3. Find the LabConstrictor app in the list, right-click on it, and select `Uninstall`.
4. A message may appear saying something like: "An error occurred while trying to uninstall xxx. It might have already been uninstalled." Click `Yes` to confirm.

This should remove the app even if the previous error message appears.

## Synchronisation is failing on GitHub Actions

It may happen that your `Sync with Template Repository` workflow fails with an error like:

```text
Error: GitHub Actions is not permitted to create or approve pull requests.
```

This means that your repository or organization does not allow GitHub Actions to create and approve pull requests. To fix this, you need to change the workflow permissions in your repository or organization settings:

> Go to Settings > Actions > General > Workflow permissions and check the option Allow GitHub Actions to create and approve pull requests.
