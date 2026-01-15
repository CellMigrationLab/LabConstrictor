# Do you want to upload a notebook?

Do you ha ve a notebook that you would like to include to your project repository? Great! Please follow the guidelines bellow to ensure a smooth upload process.

## 1. Include version controlling and requirements extraction to your notebook

Version controlling is really important to let your users know which version of the notebook they are using. Also, the requirements extraction is a key step for your notebook contribution. In order to help you with that, we have a template notebook that include two code cells that you can copy to your notebook and it will bring you both version controlling and requirements extraction.

You can check the template notebook [here](../templates/Notebook_template.ipynb).

### Version controlling cell

We recommend you include the version controlling cell at the beginning of your notebook. This cell will print out the versions of the notebook and if it is up to date with the repository. You will need to modify two code lines in order to make it work:

```python
current_version = "0.0.1"
notebook_name = "Notebook_template"
```

On `notebook_name`, please include the name of your notebook (without the `.ipynb` extension) and on `current_version`, please include the version of your notebook. Every time you make a change to your notebook, please remember to update the version number accordingly.

### Requirements extraction cell

We recommend you include the requirements extraction cell at the end of your notebook. This cell will create a `requirements.yaml` file that will include the Python version, a description of the notebook and all the packages that you are using in your notebook with their respective versions. On the next step you will learn how can you get the `requirements.yaml` file.

## 2. Generate the requirements file

Once you have included both cells to your notebook, it is time to generate the `requirements.yaml` file.

First, you will need to select a environment where you know that the notebook is working properly (e.g. a conda environment, a virtualenv or on Google Colab). Then, you will need to run the requirements extraction cell, follow the instructions and a `requirements.yaml` file will be created in the same folder where your notebook is located.

> **Important consideration on Google Colab**
> - If you have any `!pip install` commands on your notebook, please make sure to run them before running the requirements extraction cell. 
> - You will need to download the notebook `File > Download > Download .ipynb` and upload to the Colab session to allow the requirements extraction cell to create the `requirements.yaml` file. 

## 3. Upload the notebook and requirements file to the repository

You will need to go to [https://labconstrictor-form.streamlit.app/](https://labconstrictor-form.streamlit.app/) and click on `Go to update flow`. Upload your notebook and the `requirements.yaml` file that you have just created. Click on `Validate submission` and paste this GitHub repository URL and your personal access token (see [How to create a personal access token](../personal_access_token.md) if you don't have one yet). Finally, click on `Create pull request` and a pull request will be created with your notebook contribution!

To check the status of your pull request, you can go to your repository on GitHub and click on the `Pull requests` tab. You will see your pull request there. Click on the pull request to see the details. Then click on `Merge pull request` to allow your notebook to be included in the repository.

## 4. Check if the notebook has been uploaded successfully

When uploading a notebook and a requirements file our automated workflows will be triggered to check if everything is working properly. To check the status of the upload process please read [How to check the automatic workflow status](workflow_status.md).

> **IMPORTANT**: If the workflow fails, the submission of the notebook will be undone. As explained check the logs and fix the issues before re-uploading the notebook and requirements file.

# Do you want to update an existing notebook?

To update an existing notebook you just need to follow Steps 3 and 4 from above. Make sure that the name of the notebook that you are uploading is the same as the one that you want to update in the repository. Also, make sure that you have updated the version number in the version controlling cell of your notebook.

