
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
import subprocess
import os
import uuid

app = FastAPI()

REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
REPLICATE_MODEL_VERSION = "a9758cbf0aa29e34b39e7cf9c0647f6c945c8b9f3c69e4f29dfb3d4e4c2121c1"

MEDIA_DIR = "media"
os.makedirs(MEDIA_DIR, exist_ok=True)

class PromptRequest(BaseModel):
    prompt: str
    frames: int = 4

@app.post("/generate-video/")
def generate_video(request: PromptRequest):
    frame_paths = []

    for i in range(request.frames):
        response = requests.post(
            "https://api.replicate.com/v1/predictions",
            headers={
                "Authorization": f"Token {REPLICATE_API_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "version": REPLICATE_MODEL_VERSION,
                "input": {"prompt": request.prompt}
            }
        )

        output = response.json()
        if "output" not in output:
            raise HTTPException(status_code=500, detail="Error generating image.")

        image_url = output["output"][0]
        image_path = os.path.join(MEDIA_DIR, f"frame_{uuid.uuid4().hex[:8]}.png")
        img_data = requests.get(image_url).content
        with open(image_path, "wb") as handler:
            handler.write(img_data)
        frame_paths.append(image_path)

    video_filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
    video_path = os.path.join(MEDIA_DIR, video_filename)

    ffmpeg_cmd = ["ffmpeg", "-y"]
    for frame in frame_paths:
        ffmpeg_cmd.extend(["-loop", "1", "-t", "1", "-i", frame])
    filter_complex = f"[0:v]" + "".join([f"[{i}:v]" for i in range(1, request.frames)]) + f"concat=n={request.frames}:v=1:a=0[outv]"
    ffmpeg_cmd.extend(["-filter_complex", filter_complex, "-map", "[outv]", video_path])

    try:
        subprocess.run(ffmpeg_cmd, check=True)
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=500, detail="FFmpeg failed.")

    return {"video_url": f"/media/{video_filename}"}

@app.get("/media/{video_name}")
def get_video(video_name: str):
    file_path = os.path.join(MEDIA_DIR, video_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video not found.")
    return FileResponse(file_path, media_type="video/mp4")
