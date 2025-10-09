import argparse
import os
import sys
import re
import yaml
import google.generativeai as genai
from dotenv import load_dotenv

def generate_front_matter(content, model_name):
    """
    Generates a description and keywords for the given content using the Gemini API.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)
    genai.configure(api_key=api_key)

    # Add the "models/" prefix if it's not already there.
    if not model_name.startswith("models/"):
        model_name = f"models/{model_name}"

    model = genai.GenerativeModel(model_name)
    # Limit content size to avoid hitting API limits and to speed up processing
    prompt = f"""\
Analyze the following Docusaurus Markdown page content and generate a concise, SEO-friendly description and a list of relevant keywords.

**Markdown Content:**
```markdown
{content}
```

**Instructions:**
1.  **Description:** Create a single sentence description (ideally under 160 characters).
2.  **Keywords:** Provide a comma-separated list of 5 to 10 relevant keywords.

**Output Format:**
Return ONLY the description and keywords in the following format, with each key on a new line:
description: [Your generated description]
keywords: [keyword1, keyword2, keyword3]
"""

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating content with Gemini: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    """
    Main function to process the markdown file.
    """
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Generate and prepend/update Docusaurus front matter to a Markdown file."
    )
    parser.add_argument("markdown_file", help="Path to the Docusaurus Markdown file.")
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash-lite",
        help="The Gemini model to use for generation. (default: gemini-2.5-flash-lite)",
    )
    args = parser.parse_args()
    filepath = args.markdown_file

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            file_content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}", file=sys.stderr)
        sys.exit(1)

    # Use regex to separate front matter from the main content
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', file_content, re.DOTALL)

    front_matter_dict = {}
    main_content = file_content

    if match:
        front_matter_str = match.group(1)
        main_content = match.group(2)
        try:
            # Use safe_load and handle empty front matter
            front_matter_dict = yaml.safe_load(front_matter_str) or {}
        except yaml.YAMLError as e:
            print(f"Error parsing existing front matter in {filepath}: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"File '{filepath}' has existing front matter. It will be updated.")
    else:
        print(f"File '{filepath}' has no front matter. A new one will be created.")

    # Generate new description and keywords from the main content
    generated_text = generate_front_matter(main_content, args.model)

    try:
        lines = generated_text.strip().split('\n')
        description = ""
        keywords_str = ""
        for line in lines:
            if line.lower().startswith("description:"):
                description = line.split(":", 1)[1].strip()
            elif line.lower().startswith("keywords:"):
                keywords_str = line.split(":", 1)[1].strip()

        if not description or not keywords_str:
            raise ValueError("Could not parse description or keywords from model output.")

        # The model might return keywords with brackets, so remove them.
        if keywords_str.startswith('[') and keywords_str.endswith(']'):
            keywords_str = keywords_str[1:-1]

        # Clean up keywords
        keywords = [k.strip().strip('"\'') for k in keywords_str.split(',')]

    except (ValueError, IndexError) as e:
        print(f"Error parsing generated text:\n---\n{generated_text}\n---\nError: {e}", file=sys.stderr)
        sys.exit(1)

    # Update the front matter dictionary
    front_matter_dict['description'] = description
    front_matter_dict['keywords'] = keywords

    # Convert the dictionary back to a YAML string, preserving key order if possible
    new_front_matter_str = yaml.dump(front_matter_dict, default_flow_style=False, sort_keys=False)

    # Construct the new file content, ensuring a blank line after the front matter
    new_file_content = f"---\n{new_front_matter_str}---\n\n{main_content}"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_file_content)

    print(f"Successfully generated and updated front matter for {filepath}")

if __name__ == "__main__":
    main()
