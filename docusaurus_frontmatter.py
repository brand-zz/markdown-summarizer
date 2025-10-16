import argparse
import os
import sys
import re
import time
os.environ['GRPC_VERBOSITY'] = 'NONE'
import yaml
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
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

    prompt = f"""\
Analyze the following Markdown formatted page content and generate a concise, SEO-friendly description and a list of relevant keywords.

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

    model = genai.GenerativeModel(model_name)
    backoff_delay = 1  # Initial delay in seconds for exponential backoff

    while True:
        try:
            response = model.generate_content(prompt)
            return response.text
        except (
            google_exceptions.ResourceExhausted,
            google_exceptions.ServiceUnavailable,
            google_exceptions.InternalServerError,
            google_exceptions.DeadlineExceeded,
        ) as e:
            # Check if the exception has a 'retry_delay' attribute from the user's feedback
            retry_delay = getattr(e, 'retry_delay', None)

            if retry_delay is not None:
                print(f"API error occurred. Retrying in {retry_delay:.2f} seconds as suggested by the API.", file=sys.stderr)
                time.sleep(retry_delay)
            else:
                # Fallback to exponential backoff if 'retry_delay' is not present
                print(f"API error: {e}. Retrying in {backoff_delay} seconds...", file=sys.stderr)
                time.sleep(backoff_delay)
                backoff_delay = min(backoff_delay * 2, 60)  # Double the delay, capped at 60 seconds
        except Exception as e:
            # Handle non-retryable errors, such as invalid model names
            user_model_name = model_name.replace("models/", "")
            print(f"An unrecoverable error occurred with model '{user_model_name}': {e}", file=sys.stderr)

            # Attempt to list available models to help the user
            try:
                print("\nAttempting to list available models...", file=sys.stderr)
                available_models = [
                    m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods
                ]
                if available_models:
                    print("\nPlease choose from one of the following available models:", file=sys.stderr)
                    for model in sorted(available_models):
                        print(f"  - {model.replace('models/', '')}", file=sys.stderr)
                else:
                    print("Could not find any available models that support content generation.", file=sys.stderr)
            except Exception as list_e:
                print(f"\nAdditionally, failed to retrieve the list of available models: {list_e}", file=sys.stderr)
                print("Please check your API key and network connection.", file=sys.stderr)

            sys.exit(1)

def process_file(filepath, model_name, ignore_existing):
    """
    Processes a single markdown file to add or update its front matter.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            file_content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}", file=sys.stderr)
        return  # Return instead of exiting

    # Use regex to separate front matter from the main content
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', file_content, re.DOTALL)

    front_matter_dict = {}
    main_content = file_content

    if match:
        front_matter_str = match.group(1)
        main_content = match.group(2)
        try:
            front_matter_dict = yaml.safe_load(front_matter_str) or {}
        except yaml.YAMLError as e:
            print(f"Error parsing existing front matter in {filepath}: {e}", file=sys.stderr)
            return  # Return on parsing error

        if ignore_existing and front_matter_dict.get("description"):
            print(f"Skipping '{filepath}' because it already has a description and --ignore-existing is set.")
            return  # Skip the file by returning

        print(f"File '{filepath}' has existing front matter. It will be updated.")
    else:
        print(f"File '{filepath}' has no front matter. A new one will be created.")

    generated_text = generate_front_matter(main_content, model_name)

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

        if keywords_str.startswith('[') and keywords_str.endswith(']'):
            keywords_str = keywords_str[1:-1]

        keywords = [k.strip().strip('"\'') for k in keywords_str.split(',')]

    except (ValueError, IndexError) as e:
        print(f"Error parsing generated text:\n---\n{generated_text}\n---\nError: {e}", file=sys.stderr)
        return  # Return on parsing error

    front_matter_dict['description'] = description
    front_matter_dict['keywords'] = keywords

    new_front_matter_str = yaml.dump(front_matter_dict, default_flow_style=False, sort_keys=False)
    new_file_content = f"---\n{new_front_matter_str}---\n\n{main_content}"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_file_content)

    print(f"Successfully generated and updated front matter for {filepath}")


def main():
    """
    Main function to process the markdown file(s).
    """
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Generate and prepend/update Docusaurus front matter to Markdown files."
    )
    parser.add_argument(
        "markdown_files", nargs='+', help="Path(s) to the Docusaurus Markdown file(s)."
    )
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash-lite",
        help="The Gemini model to use for generation. (default: gemini-2.5-flash-lite)",
    )
    parser.add_argument(
        "--ignore-existing",
        action="store_true",
        help="Skip files that already have a description in their front matter.",
    )
    args = parser.parse_args()

    for filepath in args.markdown_files:
        process_file(filepath, args.model, args.ignore_existing)


if __name__ == "__main__":
    main()
