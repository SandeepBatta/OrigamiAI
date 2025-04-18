import os
import base64
import requests
import streamlit as st
from uuid import uuid4
from openai import OpenAI
import json

client = OpenAI()


def generate_image(prompt: str, user_id: str) -> tuple[str, str]:
    """Call OpenAI to generate an image, download it locally, return local path & revised prompt."""
    image_response = client.images.generate(
        model=st.secrets["MODEL_IMAGE"], prompt=prompt, n=1, size="1024x1024"
    )

    image_data = image_response.data[0]
    image_url = image_data.url

    revised_prompt = getattr(image_data, "revised_prompt", None)

    # fetch & save locally
    r = requests.get(image_url)
    folder = os.path.join("images", user_id)
    os.makedirs(folder, exist_ok=True)
    fname = f"{uuid4().hex}.png"
    path = os.path.join(folder, fname)
    with open(path, "wb") as f:
        f.write(r.content)

    return path, revised_prompt


def handle_response(response_text: str, response_id: str, user_id: str) -> dict:
    """Parse assistant output; if JSON instructs image, generate and return image message."""
    try:
        parsed = json.loads(response_text)
        if parsed.get("action") == "generate_image":
            image_prompt = parsed["prompt"]
            image_path, revised_prompt = generate_image(image_prompt, user_id)
            return {
                "role": "assistant",
                "type": "image",
                "content": revised_prompt,
                "url": image_path,
                "response_id": response_id,
            }
    except json.JSONDecodeError:
        # except Exception as e:
        # Normal chat response
        pass

    return {
        "role": "assistant",
        "type": "text",
        "content": response_text,
        "response_id": response_id,
    }


def send_to_ai(
    prompt,
    user_id,
    attachements=None,
    previous_response_id=None,
):
    """Send messages to OpenAI chat endpoint and dispatch to text/image handler."""
    system = {"role": "developer", "content": st.secrets["SYSTEM_PROMPT"]}
    user_msg = {
        "role": "user",
        "content": [
            {
                "type": "input_text",
                "text": prompt,
            }
        ],
    }

    if attachements:
        for attachement in attachements:
            user_msg["content"].append(
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{base64.b64encode(attachement.read()).decode("utf-8")}",
                }
            )

    messages = [system, user_msg]

    res = client.responses.create(
        model=st.secrets["MODEL_CHAT"],
        input=messages,
        previous_response_id=previous_response_id,
    )

    return handle_response(res.output_text, res.id, user_id)
