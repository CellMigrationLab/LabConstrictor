# Add or Update a Notebook

If you want to add or update a notebook in your project repository, just follow these steps to upload it smoothly.

## 1. Prepare your notebook

To ensure your notebook works with the versioning tracking provided by the LabConstrictor application, you need to add a version control cell at the top of your notebook.

> **Get the Code:** Copy the helper cell from the [Notebook Template](../templates/Notebook_template.ipynb).

### A. The Version Control Cell
Paste this cell at the top of your notebook. Then, edit these two variables:

* `notebook_name`: Enter the filename of your notebook (excluding `.ipynb`).
* `current_version`: Enter the version number (e.g., `'1.0.0'`).

Note: Each time you change the notebook's logic, update the version number so users can see there is a new version.

## 2. Generate the requirements file

Follow the steps in the [Obtain requirements of the notebook](notebook_requirements.md) guide to create the `requirements.yaml` file for your notebook.

## 3. Upload to the repository

1. Open the [LabConstrictor website](https://labconstrictor-form.streamlit.app/). If you see a `Zzzz` message for inactivity, click `Yes, get this app back up!`.
2.  Select **Go to update flow**.
3. Upload your notebook file (`.ipynb`) and the `requirements.yaml` file you created.
4.  Click **Validate submission**.
5. Enter your repository URL and your personal access token.
    * *(Don't have a token? See [How to create a personal access token](../personal_access_token.md))*
6. Click Create pull request.


## 4. Merge and Verify

If you need help merging the pull request, see the [Accept a Pull Request](accept_pull_request.md) guide for instructions. An automatic workflow will check your notebook and its dependencies.
* **Check Status:** See [How to check workflow status](workflow_status.md).
* Failure Protocol: If the workflow fails, for example, because of dependency conflicts, the system will automatically undo the merge. Check the logs, fix the problem in your local notebook or requirements, and upload again.

---

# How to Update an Existing Notebook

Updating a notebook works the same way as adding a new one:

1. Bump the version: In the top cell of your notebook, increase the `current_version` (for example, from '1.0.0' to '1.0.1').
2. Regenerate requirements: Run the bottom cell to make sure `requirements.yaml` matches the new version number.
3. Upload: Use the [LabConstrictor App](https://labconstrictor-form.streamlit.app/) to upload your file.
    * *Ensure the filename matches the existing one in the repository exactly.*

---
    
<div align="center">

[← Previous](notebook_requirements.md) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
[🏠 Home](README.md) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
[Next →](executable_creation.md)


</div>
