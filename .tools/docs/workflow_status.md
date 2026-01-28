# Check Workflow Status & Troubleshooting

When you upload a notebook or make a release, GitHub Actions starts a workflow to check your code and build the installers.

## 1. Monitor the Progress

1.  Go to the **Actions** tab in your GitHub repository.
2. You’ll see a list of recent workflows. Find the one that matches your latest commit or release.
3.  Check the status icon next to the workflow name:
![GitHub Actions Status Icons](https://docs.github.com/assets/images/help/repository/actions_status_icons.png)

## 2. How to Debug a Failure

If the workflow fails, don’t worry. The system creates an error log that’s ready for you to use.

1.  **Download the Log:**
    * Click on the failed workflow run.
    * Scroll down to the bottom of the page to the **Artifacts** section.
    * Download the artifact (usually a `.zip` file) and unzip it.

2.  **Copy & Paste into AI:**
    * Open the text file inside the folder.
    * **This file is already formatted as a prompt.** It includes all the context and error details you need.
    * Just **copy all the text** and paste it into your preferred AI tool (like ChatGPT, Gemini, or Claude). The AI will explain the error and show you how to fix your notebook or `requirements.yaml`.

---

### 💡 Best Practice for Large Updates

If you’re planning a big update, like changing several notebooks or adding complex dependencies, don’t push straight to the main branch.

Instead, **create a new branch**, make your changes there, and check that the workflows pass (✅) before merging into the main branch. This helps keep your live app working.

---

<div align="center">

[← Previous](accept_pull_request.md) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
[🏠 Home](README.md) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
[Next →](personal_access_token.md)


</div>
