# Add or Update a Notebook

Do you have a notebook that you would like to add or update an existing one in your project repository? Great! Please follow these steps to ensure a smooth upload process.

## 1. Prepare your notebook

To ensure your notebook works within the LabConstrictor application, you must add two specific helper cells. These cells handle version tracking and dependency management.

> **Get the Code:** Copy the helper cells from the [Notebook Template](../templates/Notebook_template.ipynb).

### A. The Version Control Cell
Paste this cell at the **top** of your notebook. You must edit two variables inside it:

* `notebook_name`: Enter the filename of your notebook (excluding `.ipynb`).
* `current_version`: Enter the version number (e.g., `'1.0.0'`).

> **Note:** Every time you update the notebook logic, you **must** update this version number so users know an update is available.

### B. The Requirements Extraction Cell
Paste this cell at the **very end** of your notebook.
This cell scans your imports and generates a `requirements.yaml` file containing the Python version, notebook description, and all necessary libraries.

## 2. Generate the requirements file

Once the cells are added, you need to generate the dependency file.

1.  Open your notebook in a working environment (local Conda, VirtualEnv, or Google Colab).
2.  **Run the Requirements Extraction cell.**
3.  A file named `requirements.yaml` will be created in the same folder.

> **Using Google Colab?**
> - If you have any `!pip install` commands on your notebook, please make sure to run them before running the requirements extraction cell. 
> - You will need to download the notebook `File > Download > Download .ipynb` and upload to the file system within the Colab session (on the left sidebar under the "Files" tab). 

## 3. Upload to Repository

1.  Go to the **[LabConstrictor App](https://labconstrictor-form.streamlit.app/)**.
2.  Select **Go to update flow**.
3.  Upload your **Notebook** (`.ipynb`) and the generated **Requirements** (`requirements.yaml`).
4.  Click **Validate submission**.
5.  Enter your Repository URL and **Personal Access Token**.
    * *(Don't have a token? See [How to create a personal access token](../personal_access_token.md))*
6.  Click **Create pull request**.


## 4. Merge and Verify

1.  Go to the **Pull requests** tab in your GitHub repository.
2.  Open the new request (e.g., "Add notebook X").
3.  Click **Merge pull request** to add the notebook to your main branch.

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