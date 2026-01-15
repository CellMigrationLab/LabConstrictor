# How to check the automatic workflow status?

When you upload/update a notebook in your repository or create a release to generate installer executable files, the automated workflows will be triggered to ensure that everything is working properly and make some modifications.

To check the status of these automated workflows, please follow the steps below:

1. Go to your repository on GitHub.
2. Click on the `Actions` tab. Here you will see a list of all the workflows that have been triggered in your repository.
3. Look for the workflow that corresponds to your recent upload or release. T
> If the workflow is still running, you will see a yellow dot next to it. If it has completed successfully, you will see a green checkmark. If it has failed, you will see a red cross.
4. Wait for the workflow to complete. If the workflow has completed successfully, everything has been set up correctly. If the workflow has failed, click on the workflow and go to the bottom of the page, there you will find an Artifacts section. On the Artifact section, you will have logs that you can download and unzip. Text files will be inside the unzipped folder, copy and paste that text into your favorite Large Language Model (LLM) (e.g. ChatGPT or Gemini) to get a better explanation on how to fix the issues.

>**IMPORTANT**: If you are planning on making a big update to your repository (e.g. changing many notebooks that might break the dependenciees), it is recommended to do it on a different branch.