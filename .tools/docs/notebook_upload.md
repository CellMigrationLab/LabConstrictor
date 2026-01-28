# Add or Update a Notebook

Do you have a notebook that you would like to add or update an existing one in your project repository? Great! Please follow these steps to ensure a smooth upload process.

## 1. Prepare your notebook

To ensure your notebook works within the versioning tracking that LabConstrictor application provides, you need to add a version control cell at the top of your notebook.

> **Get the Code:** Copy the helper cell from the [Notebook Template](../templates/Notebook_template.ipynb).

### A. The Version Control Cell
Paste this cell at the **top** of your notebook. You must edit two variables inside it:

* `notebook_name`: Enter the filename of your notebook (excluding `.ipynb`).
* `current_version`: Enter the version number (e.g., `'1.0.0'`).

> **Note:** Every time you update the notebook logic, you **must** update this version number so users know an update is available.

## 2. Generate the requirements file

Please follow the instructions in the [Obtain requirements of the notebook](notebook_requirements.md) guide to generate the `requirements.yaml` file for your notebook.

## 3. Upload to the repository

1.  Go to the **[LabConstrictor website](https://labconstrictor-form.streamlit.app/)**. If you find a `Zzzz` message for inactivity, please click on `Yes, get this app back up!`.
2.  Select **Go to update flow**.
3.  Upload your **Notebook** (`.ipynb`) and the generated **Requirements** (`requirements.yaml`).
4.  Click **Validate submission**.
5.  Enter your Repository URL and **Personal Access Token**.
    * *(Don't have a token? See [How to create a personal access token](../personal_access_token.md))*
6.  Click **Create pull request**.


## 4. Merge and Verify

If you need help merging the Pull Request, please follow the instructions in the [Accept a Pull Request](accept_pull_request.md) guide.

### ⚠️ Automated Validation
Merging triggers an automatic workflow to verify the notebook and dependencies.
* **Check Status:** See [How to check workflow status](workflow_status.md).
* **Failure Protocol:** If the workflow fails (e.g., due to dependency conflicts), the system will **automatically revert** the merge. You must check the logs, fix the issue in your local notebook/requirements, and repeat the upload process.

---

# How to Update an Existing Notebook

The process for updating a notebook is identical to adding a new one:

1.  **Bump the Version:** In your notebook's top cell, increase the `current_version` (e.g., from `'1.0.0'` to `'1.0.1'`).
2.  **Regenerate Requirements:** Run the bottom cell to ensure `requirements.yaml` reflects the new version number.
3.  **Upload:** Use the [LabConstrictor App](https://labconstrictor-form.streamlit.app/) to upload the file.
    * *Ensure the filename matches the existing one in the repository exactly.*

---
    
<div align="center">

[← Previous](notebook_requirements.md) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
[🏠 Home](README.md) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
[Next →](executable_creation.md)

</div>