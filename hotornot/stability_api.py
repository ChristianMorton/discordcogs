import base64
import os
import requests
from dotenv import load_dotenv

class StabilityAPI():
    def __init__(self):  # sourcery skip: raise-specific-error
        load_dotenv()
        engine_id = "stable-diffusion-v1-5"
        api_host = os.getenv('https://api.stability.ai')
        api_key = os.getenv("STABILITY_API_KEY")
        if self.api_key is None:
            raise Exception("Missing Stability API key.")

    def generate_image(self, prompt_text):
        prompt_text = "a mugshot of a homeless white woman, middle aged, on drugs --photorealism"
        response = requests.post(f"{StabilityAPI.api_host}/v1/generation/{StabilityAPI.engine_id}/text-to-image",headers={"Content-Type": "application/json","Accept": "application/json","Authorization": "Bearer {StabilityAPI.api_key}"})
        json={"text_prompts": [
        {
        "text": prompt_text
        }
        ],"cfg_scale": 7,"clip_guidance_preset": "FAST_BLUE","height": 512,"width": 512,"samples": 1,"steps": 30,}
        if response.status_code != 200:
            raise Exception("Non-200 response: " + str(response.text))

        data = response.json()

        for i, image in enumerate(data["artifacts"]):
            with open(f"C:\\Users\\davec\\OneDrive\\Documents\\GitHub\\discordcogs\\hotornot\\v1_txt2imgsss_{i}.png", "wb") as f:
                f.write(base64.b64decode(image["base64"]))

        return f"C:\\Users\\davec\\OneDrive\\Documents\\GitHub\\discordcogs\\hotornot\\v1_txt2imgsss_0.png"  # Returns the path of the generated image
    
