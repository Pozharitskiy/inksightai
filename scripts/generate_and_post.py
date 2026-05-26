import os
import sys
from openai import OpenAI
import requests

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
PINTEREST_ACCESS_TOKEN = os.environ["PINTEREST_ACCESS_TOKEN"]
PINTEREST_BOARD_ID = os.environ["PINTEREST_BOARD_ID"]

client = OpenAI(api_key=OPENAI_API_KEY)


def generate_prompt():
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
    return response.choices[0].message.content.strip()


def generate_image(prompt):
    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024",
        quality="medium",
        n=1
    )
    return response.data[0].b64_json


def post_to_pinterest(image_b64, prompt):
    title = prompt[:50]
    description = (
        f"{prompt} #tattoo #tattoodesign #tattooart #tattooflash #tattooideas #tattooinspo"
    )
    payload = {
        "board_id": PINTEREST_BOARD_ID,
        "title": title,
        "description": description,
        "media_source": {
            "source_type": "image_base64",
            "content_type": "image/png",
            "data": image_b64
        }
    }
    headers = {
        "Authorization": f"Bearer {PINTEREST_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    response = requests.post(
        "https://api.pinterest.com/v5/pins",
        json=payload,
        headers=headers
    )
    response.raise_for_status()
    return response.json()


def main():
    print("=== Tattoo Pinterest Poster ===")

    print("Generating prompt...")
    try:
        prompt = generate_prompt()
    except Exception as e:
        print(f"ERROR: Failed to generate prompt: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Prompt: {prompt}")

    print("Generating image with DALL-E 3...")
    try:
        image_b64 = generate_image(prompt)
    except Exception as e:
        print(f"ERROR: Failed to generate image: {e}", file=sys.stderr)
        sys.exit(1)
    print("Image generated (base64)")

    print("Posting to Pinterest...")
    try:
        result = post_to_pinterest(image_b64, prompt)
    except requests.HTTPError as e:
        print(f"ERROR: Pinterest API returned {e.response.status_code}: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to post to Pinterest: {e}", file=sys.stderr)
        sys.exit(1)

    pin_id = result.get("id", "unknown")
    print(f"SUCCESS: Pin posted! ID: {pin_id}")


if __name__ == "__main__":
    main()
