
from fastapi import APIRouter, Query
from bs4 import BeautifulSoup
import requests

router = APIRouter()

@router.get("/amazon/buscar")
def buscar_amazon(termo: str = Query(..., description="Produto a buscar na Amazon")):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    termo_formatado = termo.replace(" ", "+")
    url = f"https://www.amazon.com.br/s?k={termo_formatado}"

    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        return {"erro": str(e)}

    resultados = []
    produtos = soup.select("div.s-result-item")

    for item in produtos:
        nome = item.select_one("h2 a span")
        link = item.select_one("h2 a")
        preco_inteiro = item.select_one("span.a-price-whole")
        preco_centavos = item.select_one("span.a-price-fraction")

        if nome and link:
            titulo = nome.text.strip()
            href = "https://www.amazon.com.br" + link["href"]
            preco = None
            if preco_inteiro and preco_centavos:
                preco = f"R$ {preco_inteiro.text.strip()},{preco_centavos.text.strip()}"

            resultados.append({
                "nome": titulo,
                "preco": preco,
                "link": href
            })

        if len(resultados) >= 5:
            break

    return resultados
