
# API de Vídeo com FastAPI + FFmpeg + Replicate

## Como usar

1. Faça deploy no Render.com com esse projeto.
2. Configure a variável de ambiente:
   - `REPLICATE_API_TOKEN` com sua chave da API Replicate.
3. Use o endpoint POST `/generate-video/` com o corpo:

```json
{
  "prompt": "a futuristic city at night",
  "frames": 4
}
```

4. O retorno será:

```json
{
  "video_url": "/media/video_xyz.mp4"
}
```

5. Acesse no navegador:
```
https://seu-app.onrender.com/media/video_xyz.mp4
```
