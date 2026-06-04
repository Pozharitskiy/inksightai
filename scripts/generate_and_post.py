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

HF_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"

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
                    "Generate a tattoo image generation prompt for a 2x2 grid of 4 design variations.\n"
                    "Randomly pick one theme from: wolf, skull, snake, eagle, rose, dragon, "
                    "koi fish, phoenix, lion, geometric mandala, butterfly, raven, bear, "
                    "compass, anchor, lettering.\n"
                    "Randomly pick one style from: blackwork, fine line, traditional american, "
                    "neo-traditional, watercolor, dotwork, japanese, celtic, ornamental.\n"
                    "Format: 2x2 grid of 4 different [subject] tattoo design variations, "
                    "[style] tattoo style, each variation slightly different pose or composition, "
                    "intricate details, high contrast, pure white background, flat lay, PNG format.\n"
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
        response = requests.post(HF_URL, headers=headers, json=payload, timeout=120)

        if response.status_code == 200:
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.write(response.content)
            tmp.close()
            print(f"Image saved to: {tmp.name} ({len(response.content)} bytes)")
            return tmp.name

        if response.status_code == 503:
            wait = 20 * attempt
            print(f"Model loading (503), waiting {wait}s...")
            time.sleep(wait)
            continue

        print(f"ERROR: HuggingFace returned {response.status_code}: {response.text[:200]}", file=sys.stderr)
        sys.exit(1)

    print("ERROR: HuggingFace model failed to load after retries", file=sys.stderr)
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

            # Dismiss cookie dialog if present
            try:
                page.wait_for_selector('text="Accept all"', timeout=5000)
                page.click('text="Accept all"')
                print("Accepted cookies")
                page.wait_for_timeout(1000)
            except PlaywrightTimeoutError:
                pass

            page.wait_for_selector('input[name="id"]', timeout=15000)
            page.fill('input[name="id"]', PINTEREST_EMAIL)
            page.fill('input[name="password"]', PINTEREST_PASSWORD)
            page.click('button[type="submit"]')
            print("Submitted login form...")

            # Wait for logged-in state — home feed or profile nav
            page.wait_for_selector('[data-test-id="header-profile"]', timeout=25000)
            print("Logged in successfully")

            # Navigate to pin creation
            print("Navigating to pin creation tool...")
            page.goto("https://www.pinterest.com/pin-creation-tool/", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            # Upload image (input is hidden, use force)
            print("Uploading image...")
            page.wait_for_selector('input[type="file"]', timeout=15000, state="attached")
            page.locator('input[type="file"]').set_input_files(image_path)
            print("Image uploaded")

            # Wait for image to process
            page.wait_for_timeout(3000)

            # Fill title
            print("Filling title...")
            page.wait_for_selector('#storyboard-selector-title', timeout=15000, state="visible")
            page.fill('#storyboard-selector-title', title)
            print(f"Title filled: {title}")

            # Fill description (contenteditable div)
            print("Filling description...")
            page.wait_for_selector('div[contenteditable="true"]', timeout=10000, state="visible")
            page.click('div[contenteditable="true"]')
            page.keyboard.type(description)
            print("Description filled")

            # Select board — scroll down first so it's visible
            print(f"Selecting board: {PINTEREST_BOARD_NAME}...")
            page.keyboard.press("End")
            page.wait_for_timeout(1000)
            board_btn = page.get_by_text("Выберите доску", exact=False).or_(
                page.get_by_text("Choose a board", exact=False)
            ).first
            board_btn.wait_for(timeout=10000, state="visible")
            board_btn.click()
            page.wait_for_timeout(1000)

            # Search for board
            search = page.locator('input[placeholder*="Поиск"]').or_(
                page.locator('input[placeholder*="Search"]')
            ).first
            search.wait_for(timeout=5000, state="visible")
            search.fill(PINTEREST_BOARD_NAME)
            page.wait_for_timeout(1000)

            # Click the board option
            board_option = page.get_by_text(PINTEREST_BOARD_NAME, exact=True).last
            board_option.wait_for(timeout=10000, state="visible")
            board_option.click()
            print("Board selected")

            # Publish
            print("Publishing pin...")
            page.locator('button:has-text("Опубликовать"), button:has-text("Publish")').first.click()
            page.wait_for_timeout(5000)
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
