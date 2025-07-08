
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
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

app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

@app.get("/", response_class=HTMLResponse)
def home():
    return '''
    <html>
    <head>
        <title>Gerador de Vídeos com IA</title>
        <style>
            body { font-family: sans-serif; padding: 40px; background: #f4f4f4; }
            input, button { padding: 10px; font-size: 16px; margin: 5px; width: 100%; max-width: 400px; }
            video { margin-top: 20px; max-width: 100%; border: 1px solid #ccc; }
            .container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 8px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Gerar Vídeo com IA (Replicate)</h2>
            <form action="/generate-video-form" method="post">
                <input type="text" name="prompt" placeholder="Descreva a cena..." required><br>
                <input type="number" name="frames" value="4" min="2" max="8"><br>
                <button type="submit">Gerar Vídeo</button>
            </form>
        </div>
    </body>
    </html>
    '''

@app.post("/generate-video-form", response_class=HTMLResponse)
def generate_video_form(prompt: str = Form(...), frames: int = Form(4)):
    frame_paths = []

    for _ in range(frames):
        response = requests.post(
            "https://api.replicate.com/v1/predictions",
            headers={
                "Authorization": f"Token {REPLICATE_API_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "version": REPLICATE_MODEL_VERSION,
                "input": {"prompt": prompt}
            }
        )

        output = response.json()
        if "output" not in output:
            raise HTTPException(status_code=500, detail="Erro ao gerar imagem com IA.")

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

    filter_complex = "".join([f"[{i}:v]" for i in range(len(frame_paths))])
    filter_complex = f"{filter_complex}concat=n={len(frame_paths)}:v=1:a=0[outv]"

    ffmpeg_cmd.extend(["-filter_complex", filter_complex, "-map", "[outv]", video_path])

    try:
        subprocess.run(ffmpeg_cmd, check=True)
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=500, detail="Erro ao gerar vídeo com FFmpeg.")

    return f'''
    <html>
    <body style="font-family:sans-serif; text-align:center; padding:40px;">
        <h2>Vídeo Gerado com Sucesso!</h2>
        <video controls autoplay loop src="/media/{video_filename}"></video><br><br>
        <a href="/">🔙 Gerar novo vídeo</a>
    </body>
    </html>
    '''
