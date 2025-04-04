from openai import OpenAI
import json
import base64
import streamlit as st


# Function to encode the image
def encode_image(image):
    return base64.b64encode(image).decode("utf-8")


# Set up OpenAI API client
client = OpenAI()


# ----------- Image Generation -----------
def generate_image(prompt: str):
    image_response = client.images.generate(
        model=st.secrets["MODEL_IMAGE"], prompt=prompt, n=1, size="1024x1024"
    )

    image_data = image_response.data[0]
    image_url = image_data.url

    revised_prompt = getattr(image_data, "revised_prompt", None)
    return image_url, revised_prompt


# ----------- Dispatcher -----------
def handle_response(response_text, response_id) -> dict:

    try:
        # Try parsing as JSON to detect image request
        parsed = json.loads(response_text)
        if parsed.get("action") == "generate_image":
            image_prompt = parsed["prompt"]
            image_url, revised_prompt = generate_image(image_prompt)
            return {
                "role": "assistant",
                "type": "image",
                "content": revised_prompt,
                "url": image_url,
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


# ----------- Chat Handling -----------
def send_to_ai(prompt: str, attachements=None, response_id=None):
    developer_message = {"role": "developer", "content": st.secrets["SYSTEM_PROMPT"]}
    user_message = {
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
            user_message["content"].append(
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{base64.b64encode(attachement.read()).decode("utf-8")}",
                }
            )

    messages = [developer_message, user_message]

    response = client.responses.create(
        model=st.secrets["MODEL_CHAT"], input=messages, previous_response_id=response_id
    )

    return handle_response(response.output_text, response.id)
