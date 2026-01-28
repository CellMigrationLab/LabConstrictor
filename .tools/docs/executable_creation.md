# Create a Installer Files 

Have you uploaded notebooks to your repository and are you ready to share your work? Great! Please follow the guidelines below to ensure a smooth executable creation process.

### ⚠️ Please check before proceeding:

Go to the Actions tab in your repository. Ensure there are no workflows currently running. If a workflow is in progress, wait for it to finish. Publishing a release while other jobs are running can cause build conflicts.

## 1. Draft a new release

1. Go to your repository's main page.
2. Click on Releases (usually on the right sidebar).
3. Click on `Create a new release` and fill in the following information:
   - **Tag**: click on `Create a new tag` and enter a version number e.g. `0.0.1`.
      > **IMPORTANT**: Make sure that it follows a semantic versioning format (MAJOR.MINOR.PATCH) e.g. `1.0.0`, `1.2.3`, `2.1.0`.
   - **Release title**: enter a title for your release e.g. `Initial release`.
   - **Description** *(optional)*: enter a description for your release e.g. `This is the initial release of my project.`

## 2. Publish the release

Once you have filled in all the information, click on `Publish release`. This will trigger our automated workflows to create the installer executable files for your notebooks. To check the status of the executable creation process please read [How to check the automatic workflow status](workflow_status.md).

## 3. Download the executable files

Once the automated workflow has completed successfully, you will be able to download the installer following the instructions in [How to download the executable files](download_executable.md).


---

<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 40px;">
  <a href="notebook_upload.md" style="flex: 1; text-align: left;">← Previous</a>
  <a href="README.md" style="flex: 1; text-align: center;">🏠 Home</a>
  <a href="download_executable.md" style="flex: 1; text-align: right;">Next →</a>
</div>