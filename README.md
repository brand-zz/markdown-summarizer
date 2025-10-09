# Docusaurus Front Matter Generator

This script uses the Gemini API to automatically generate and prepend front matter (description and keywords) to Docusaurus Markdown files.

## Setup

1.  **Set Gemini API Key:**

    You need to have a Gemini API key. You can obtain one from [Google AI Studio](https://aistudio.google.com/).

    Set the API key as an environment variable:
    ```bash
    export GEMINI_API_KEY="YOUR_API_KEY"
    ```

2.  **Install Dependencies:**

    Install the necessary Python packages using pip:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the script from your terminal, passing the path to the Markdown file as an argument:

```bash
python docusaurus_frontmatter.py /path/to/your/markdown-file.md
```

The script will:
- Read the content of the Markdown file.
- Generate a new description and keywords using the Gemini API.
- Update the front matter with the new `description` and `keywords`.

If the file already has front matter, the script will overwrite the `description` and `keywords` fields, preserving any other existing data. If the file has no front matter, it will be created.