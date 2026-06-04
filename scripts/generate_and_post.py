import os
import sys
import time
import tempfile
import requests
from openai import OpenAI
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
HUGGINGFACE_TOKEN = os.environ["HUGGINGFACE_TOKEN"]
PINTEREST_EMAIL = os.environ["PINTEREST_EMAIL"]
PINTEREST_PASSWORD = os.environ["PINTEREST_PASSWORD"]
PINTEREST_BOARD_NAME = os.environ["PINTEREST_BOARD_NAME"]

SDXL_URL = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"

client = OpenAI(api_key=OPENAI_API_KEY)


def generate_prompt():
    print("=== Step 1: Generating prompt ===")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a tattoo prompt generator. Return ONLY the image generation prompt, no explanations, no quotes."
            },
            {
                "role": "user",
                "content": (
                    "Generate a tattoo image generation prompt.\n"
                    "Randomly pick one theme from: wolf, skull, snake, eagle, rose, dragon, "
                    "koi fish, phoenix, lion, geometric mandala, butterfly, raven, bear, "
                    "compass, anchor, lettering.\n"
                    "Randomly pick one style from: blackwork, fine line, traditional american, "
                    "neo-traditional, watercolor, dotwork, japanese, celtic, ornamental.\n"
                    "Format: [subject], [style] tattoo style, intricate details, "
                    "high contrast, pure white background, PNG format.\n"
                    "Return ONLY the prompt."
                )
            }
        ]
    )
    prompt = response.choices[0].message.content.strip()
    print(f"Prompt: {prompt}")
    return prompt


def generate_image(prompt):
    print("=== Step 2: Generating image via Hugging Face ===")
    headers = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}
    payload = {"inputs": prompt}

    max_retries = 5
    for attempt in range(1, max_retries + 1):
        print(f"Attempt {attempt}/{max_retries}...")
        response = requests.post(SDXL_URL, headers=headers, json=payload, timeout=120)

        if response.status_code == 200:
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.write(response.content)
            tmp.close()
            print(f"Image saved to: {tmp.name}")
            return tmp.name

        if response.status_code == 503:
            wait = 20 * attempt
            print(f"Model loading (503), waiting {wait}s...")
            time.sleep(wait)
            continue

        print(f"ERROR: Hugging Face returned {response.status_code}: {response.text}", file=sys.stderr)
        sys.exit(1)

    print("ERROR: Hugging Face model failed to load after retries", file=sys.stderr)
    sys.exit(1)


def post_to_pinterest(image_path, prompt):
    print("=== Step 3: Posting to Pinterest via Playwright ===")
    title = prompt[:50]
    description = (
        f"{prompt} #tattoo #tattoodesign #tattooart #tattooflash "
        "#tattooideas #tattooinspo #tattooartist #inked #tattooflash"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            # Login
            print("Navigating to Pinterest login...")
            page.goto("https://www.pinterest.com/login/", wait_until="networkidle")
            page.wait_for_selector('input[name="id"]', timeout=15000)
            page.fill('input[name="id"]', PINTEREST_EMAIL)
            page.fill('input[name="password"]', PINTEREST_PASSWORD)
            page.click('button[type="submit"]')
            print("Submitted login form...")
            page.wait_for_url("**/", timeout=20000)
            print("Logged in successfully")

            # Navigate to pin creation
            print("Navigating to pin creation tool...")
            page.goto("https://www.pinterest.com/pin-creation-tool/", wait_until="networkidle")

            # Upload image
            print("Uploading image...")
            page.wait_for_selector('input[type="file"]', timeout=15000)
            page.set_input_files('input[type="file"]', image_path)
            print("Image uploaded")

            # Wait for image to process
            page.wait_for_timeout(3000)

            # Fill title
            print("Filling title...")
            title_selector = '[placeholder="Add your title"]'
            page.wait_for_selector(title_selector, timeout=15000)
            page.click(title_selector)
            page.fill(title_selector, title)

            # Fill description
            print("Filling description...")
            desc_selector = '[placeholder="Tell everyone what your Pin is about"]'
            page.wait_for_selector(desc_selector, timeout=10000)
            page.click(desc_selector)
            page.fill(desc_selector, description)

            # Select board
            print(f"Selecting board: {PINTEREST_BOARD_NAME}...")
            board_selector = '[data-test-id="board-dropdown-select-button"]'
            page.wait_for_selector(board_selector, timeout=10000)
            page.click(board_selector)

            # Search for board
            page.wait_for_selector('[placeholder="Search"]', timeout=5000)
            page.fill('[placeholder="Search"]', PINTEREST_BOARD_NAME)
            page.wait_for_timeout(1000)

            # Click the board option
            board_option = page.locator(f'[data-test-id="board-option"] >> text="{PINTEREST_BOARD_NAME}"').first
            board_option.wait_for(timeout=10000)
            board_option.click()
            print("Board selected")

            # Publish
            print("Publishing pin...")
            publish_btn = page.locator('[data-test-id="board-dropdown-save-button"]')
            publish_btn.wait_for(timeout=10000)
            publish_btn.click()

            # Wait for success
            page.wait_for_selector('[data-test-id="pin-saved-success"]', timeout=20000)
            print("SUCCESS: Pin published!")

        except PlaywrightTimeoutError as e:
            print(f"ERROR: Timeout - {e}", file=sys.stderr)
            screenshot_path = "/tmp/error_screenshot.png"
            page.screenshot(path=screenshot_path)
            print(f"Screenshot saved to {screenshot_path}", file=sys.stderr)
            browser.close()
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            screenshot_path = "/tmp/error_screenshot.png"
            page.screenshot(path=screenshot_path)
            print(f"Screenshot saved to {screenshot_path}", file=sys.stderr)
            browser.close()
            raise

        browser.close()


def main():
    image_path = None
    try:
        prompt = generate_prompt()
        image_path = generate_image(prompt)
        post_to_pinterest(image_path, prompt)
    finally:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
            print(f"Cleaned up temp file: {image_path}")


if __name__ == "__main__":
    main()
