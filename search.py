from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/")
def buscar_produtos(keyword: str, plataforma: str = "mercadolivre"):
    if plataforma == "mercadolivre":
        return JSONResponse(content={
            "plataforma": plataforma,
            "produtos": [
                {
                    "nome": "Kindle Paperwhite",
                    "preco": "R$ 599,00",
                    "avaliacao": "4.8",
                    "imagem": "https://http2.mlstatic.com/D_NQ_NP_2X_638777-MLU72854485429_112023-F.webp",
                    "link": "https://mercadolivre.com.br/kindle-paperwhite"
                }
            ]
        })
    return JSONResponse(content={"erro": "Plataforma não suportada"}, status_code=400)