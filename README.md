
# FastAPI + Replicate + FFmpeg (Deploy no Render)

## Como usar:

1. Crie conta em: https://render.com
2. Crie um novo projeto do tipo **Web Service**
3. Faça upload ou conecte este repositório
4. Defina a variável de ambiente:
   - `REPLICATE_API_TOKEN` com sua chave da API

O serviço irá:
- Receber um prompt de texto
- Gerar imagens com IA
- Juntar em um vídeo (MP4)
- Retornar a URL do vídeo para consumo via `/media/`

Exemplo de uso:

POST `/generate-video/`
```json
{
  "prompt": "a city of robots at night",
  "frames": 4
}
```

Retorno:
```json
{
  "video_url": "/media/video_xxx.mp4"
}
```
