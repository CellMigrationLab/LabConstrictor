# Do you want to create an installer executable file with your notebooks?

Have you uploaded notebooks to your repository and now you want to create an installer executable file so that your users can run your notebooks easily? Great! Please follow the guidelines below to ensure a smooth executable creation process.

## 1. Create a release on your repository

On GitHub, go to your repository and click on the `Releases` tab. Then click on `Draft a new release`. You will need to fill in the following information:
 - Tag: click on `Create a new tag` and enter a version number e.g. `0.0.1`.
    > **IMPORTANT**: Make sure that it follows a semantic versioning format (MAJOR.MINOR.PATCH) e.g. `1.0.0`, `1.2.3`, `2.1.0`.
 - Release title: enter a title for your release e.g. `Initial release`.
 - Description: enter a description for your release e.g. `This is the initial release of my project.`

## 2. Publish the release

Once you have filled in all the information, click on `Publish release`. This will trigger our automated workflows to create the installer executable files for your notebooks. To check the status of the executable creation process please read [How to check the automatic workflow status](workflow_status.md).

> **IMPORTANT**: Check that no other workflows (on `Actions` section) are running on your repository before publishing a new release. If there are other workflows running, please wait for them to finish before publishing a new release to avoid conflicts.

## 3. Download the executable files

Once the automated workflow has completed successfully, you will be able to download the installer following the instructions in [How to download the executable files](download_executable.md).