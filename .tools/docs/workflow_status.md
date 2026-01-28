# Check Workflow Status & Troubleshooting

Whenever you upload a notebook or create a release, GitHub Actions automatically triggers a workflow to validate your code and build the installers.

## 1. Monitor the Progress

1.  Go to the **Actions** tab in your GitHub repository.
2.  You will see a list of recent workflows. Look for the one matching your recent commit or release.
3.  Check the status icon next to the workflow name:
![GitHub Actions Status Icons](https://docs.github.com/assets/images/help/repository/actions_status_icons.png)

## 2. How to Debug a Failure

If the workflow fails, don't panic. The system automatically generates a "ready-to-ask" error log for you.

1.  **Download the Log:**
    * Click on the failed workflow run.
    * Scroll down to the bottom of the page to the **Artifacts** section.
    * Download the artifact (usually a `.zip` file) and unzip it.

2.  **Copy & Paste into AI:**
    * Open the text file inside the folder.
    * **We have already formatted this file as a prompt.** It contains the necessary context and error details.
    * simply **Copy all the text** and paste it directly into your favorite AI tool (ChatGPT, Gemini, Claude, etc.). The AI will explain the error and tell you exactly how to fix your notebook or `requirements.yaml`.

---

### 💡 Best Practice for Large Updates

If you are planning a major update (e.g., changing many notebooks or adding complex dependencies), do not push directly to the main branch.

Instead, **create a new branch**, make your changes there, and verify that the workflows pass (✅) before merging into your main branch. This prevents breaking the live version of your application.

---

<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 40px;">
  <a href="accept_pull_request.md" style="flex: 1; text-align: left;">← Previous</a>
  <a href="README.md" style="flex: 1; text-align: center;">🏠 Home</a>
  <a href="personal_access_token.md" style="flex: 1; text-align: right;">Next →</a>
</div>