Create a GitHub Actions workflow that automatically generates and posts 
tattoo designs to Pinterest.

## What it should do:
- Run every 2 hours via cron schedule
- Generate a tattoo prompt using OpenAI GPT-4o-mini
- Generate an image using DALL-E 3 (1024x1024, standard quality)
- Post the image to Pinterest as a Pin

## Tech stack:
- Python 3.11
- GitHub Actions (workflow file)
- No external dependencies except: openai, requests

## Pinterest API:
- Use Pinterest API v5
- Endpoint: POST https://api.pinterest.com/v5/pins
- Auth: Bearer token
- To post a pin with image URL:
  POST /v5/pins
  {
    "board_id": "<BOARD_ID>",
    "title": "<first 50 chars of prompt>",
    "description": "<full prompt> #tattoo #tattoodesign #tattooart 
                    #tattooflash #tattooideas #tattooinspo",
    "media_source": {
      "source_type": "image_url",
      "url": "<dalle image url>"
    }
  }

## Prompt generation:
System: "You are a tattoo prompt generator. Return ONLY the image 
generation prompt, no explanations, no quotes."

User: "Generate a tattoo image generation prompt.
Randomly pick one theme from: wolf, skull, snake, eagle, rose, dragon, 
koi fish, phoenix, lion, geometric mandala, butterfly, raven, bear, 
compass, anchor, lettering.
Randomly pick one style from: blackwork, fine line, traditional american, 
neo-traditional, watercolor, dotwork, japanese, celtic, ornamental.
Format: [subject], [style] tattoo style, intricate details, 
high contrast, pure white background, PNG format.
Return ONLY the prompt."

## GitHub Actions:
- Cron: every 2 hours  
- All secrets via GitHub Secrets:
  - OPENAI_API_KEY
  - PINTEREST_ACCESS_TOKEN
  - PINTEREST_BOARD_ID
- Add simple logging so we can see in Actions logs what prompt 
  was generated and whether pin was posted successfully
- Handle errors gracefully (if Pinterest or OpenAI fails — 
  log error, don't crash silently)

## File structure:
.github/workflows/tattoo_poster.yml
scripts/generate_and_post.py

## After creating files, show me:
1. Exact GitHub Secrets I need to add and where to get them
2. How to get Pinterest Board ID
3. How to get Pinterest Access Token (which scopes needed)