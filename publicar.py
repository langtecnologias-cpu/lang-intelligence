# -*- coding: utf-8 -*-
"""
LANG Intelligence: publica no Instagram (API oficial da Meta, "Instagram API com login do Instagram")
o que está agendado em calendario.csv: imagens (feed), STORIES e REELS.
Roda no GitHub Actions, mas funciona em qualquer lugar com Python 3.

Segredos / variáveis de ambiente:
  IG_USER_ID   id numérico da conta profissional @langintelligence
  IG_TOKEN     token de acesso de longa duração (60 dias; o script o renova a cada execução)
  BASE_URL     endereço público do repositório no GitHub Pages, ex.: https://usuario.github.io/lang-intelligence
Opcional:
  API_VERSION  ex.: v23.0 (vazio = versão padrão do app)

Uso:
  python publicar.py                  publica tudo que já está na hora e ainda não foi publicado
  python publicar.py --simular        só mostra o que faria (não precisa de credenciais)
  python publicar.py --data=2026-10-27 --simular    simula como se hoje fosse essa data
  python publicar.py --id=S01         publica agora a linha com esse id (teste), ignorando data/hora
  python publicar.py --renovar        só renova o token
  python publicar.py --verificar      confere se o token e o IG_USER_ID funcionam (sem publicar)
"""
import os, sys, csv, time, json, datetime, urllib.request, urllib.parse, urllib.error
from zoneinfo import ZoneInfo

AQUI = os.path.dirname(os.path.abspath(__file__))
IG_USER_ID = os.environ.get("IG_USER_ID", "").strip()
TOKEN = os.environ.get("IG_TOKEN", "").strip()
BASE_URL = os.environ.get("BASE_URL", "").strip().rstrip("/")
VER = os.environ.get("API_VERSION", "").strip()
G = "https://graph.instagram.com" + (f"/{VER}" if VER else "")
SIMULAR = "--simular" in sys.argv
arg = lambda nome: next((a.split("=", 1)[1] for a in sys.argv if a.startswith(f"--{nome}=")), None)
CALENDARIOS = [("calendario.csv", "postado.csv")]


def chamar(metodo, caminho, params=None):
    params = dict(params or {}, access_token=TOKEN)
    dados = urllib.parse.urlencode(params)
    url = f"{G}/{caminho}"
    req = urllib.request.Request(f"{url}?{dados}") if metodo == "GET" else urllib.request.Request(url, data=dados.encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        corpo = e.read().decode()
        corpo = corpo.replace(TOKEN, "***") if TOKEN else corpo
        raise SystemExit(f"Erro da API ({e.code}) em {caminho}: {corpo}")


def esperar(container):
    for _ in range(72):  # até ~6 min
        st = chamar("GET", container, {"fields": "status_code,status"})
        if st.get("status_code") == "FINISHED":
            return
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise SystemExit(f"O Instagram não conseguiu processar a mídia: {st}")
        time.sleep(5)
    raise SystemExit("Tempo esgotado esperando o Instagram processar a mídia.")


def conferir_url(url):
    """a mídia precisa estar acessível publicamente; avisa cedo se o Pages ainda não publicou"""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=60) as r:
            if r.status != 200:
                raise SystemExit(f"Arquivo não acessível ({r.status}): {url}")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Arquivo não acessível ({e.code}): {url} — o GitHub Pages está ligado e já publicou os arquivos?")


def publicar_container(c):
    esperar(c)
    return chamar("POST", f"{IG_USER_ID}/media_publish", {"creation_id": c})["id"]


def publicar_reel(arquivos, legenda):
    url = f"{BASE_URL}/{arquivos[0]}"; conferir_url(url)
    return publicar_container(chamar("POST", f"{IG_USER_ID}/media",
               {"media_type": "REELS", "video_url": url, "caption": legenda, "share_to_feed": "true",
                "thumb_offset": "3000"})["id"])   # capa = quadro aos 3 s (o 1º quadro é escuro: o vídeo abre em fade)


def publicar_reel_teste(arquivos, legenda):
    """Reel de teste (trial reel): mostrado primeiro só a quem não segue a conta; o envio aos seguidores é manual no app."""
    url = f"{BASE_URL}/{arquivos[0]}"; conferir_url(url)
    return publicar_container(chamar("POST", f"{IG_USER_ID}/media",
               {"media_type": "REELS", "video_url": url, "caption": legenda,
                "trial_params": json.dumps({"graduation_strategy": "MANUAL"})})["id"])


def publicar_carrossel(arquivos, legenda):
    filhos = []
    for a in arquivos:
        url = f"{BASE_URL}/{a}"; conferir_url(url)
        filhos.append(chamar("POST", f"{IG_USER_ID}/media", {"image_url": url, "is_carousel_item": "true"})["id"])
    for f in filhos:
        esperar(f)
    return publicar_container(chamar("POST", f"{IG_USER_ID}/media", {"media_type": "CAROUSEL", "children": ",".join(filhos), "caption": legenda})["id"])


def publicar_imagem(arquivos, legenda):
    url = f"{BASE_URL}/{arquivos[0]}"; conferir_url(url)
    return publicar_container(chamar("POST", f"{IG_USER_ID}/media", {"image_url": url, "caption": legenda})["id"])


def publicar_story(arquivos, legenda):
    url = f"{BASE_URL}/{arquivos[0]}"; conferir_url(url)
    campo = "video_url" if url.lower().endswith((".mp4", ".mov")) else "image_url"
    return publicar_container(chamar("POST", f"{IG_USER_ID}/media", {"media_type": "STORIES", campo: url})["id"])


FUNCOES = {"reel": publicar_reel, "reel_teste": publicar_reel_teste, "carrossel": publicar_carrossel, "imagem": publicar_imagem, "story": publicar_story}


def renovar():
    r = chamar("GET", "refresh_access_token", {"grant_type": "ig_refresh_token"})
    novo, dias = r.get("access_token", ""), round(r.get("expires_in", 0) / 86400)
    print(f"Token renovado: vale mais ~{dias} dias.")
    if novo and novo != TOKEN:
        print("::warning::O Instagram devolveu um token DIFERENTE. Atualize o segredo IG_TOKEN com o novo valor (veja o LEIA-ME).")
    return dias


def verificar():
    r = chamar("GET", "me", {"fields": "user_id,username,account_type"})
    print("Conta:", r)
    if IG_USER_ID and str(r.get("user_id", r.get("id", ""))) != IG_USER_ID:
        print("::warning::IG_USER_ID não bate com a conta do token:", r)


def ler_log():
    feitos = set()
    for _, log in CALENDARIOS:
        p = f"{AQUI}/{log}"
        if os.path.exists(p):
            feitos |= {l.split(";")[0] for l in open(p, encoding="utf-8").read().splitlines() if l}
    return feitos


def main():
    if "--renovar" in sys.argv:
        return renovar()
    if "--verificar" in sys.argv:
        return verificar()
    agora = datetime.datetime.now(ZoneInfo("America/Sao_Paulo"))
    data_hoje = arg("data") or agora.date().isoformat()
    hora_agora = agora.strftime("%H:%M") if not arg("data") else "23:59"
    linhas = []
    for cal, log in CALENDARIOS:
        if not os.path.exists(f"{AQUI}/{cal}"):
            continue
        with open(f"{AQUI}/{cal}", encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f, delimiter=";"):
                r["_log"] = log
                linhas.append(r)
    linhas.sort(key=lambda r: (r["data"], r["horario"]))
    feitos = ler_log()
    if arg("id"):
        devidos = [r for r in linhas if r["id"] == arg("id")]
    else:
        devidos = [r for r in linhas if r["id"] not in feitos and (r["data"], r["horario"]) <= (data_hoje, hora_agora)]
        # só recupera atrasos de até 2 dias, para nunca despejar uma fila antiga de uma vez
        limite = (datetime.date.fromisoformat(data_hoje) - datetime.timedelta(days=2)).isoformat()
        devidos = [r for r in devidos if r["data"] >= limite]
    if not devidos:
        print(f"Nada a publicar agora ({data_hoje} {hora_agora}).")
        return
    if not SIMULAR and not (IG_USER_ID and TOKEN and BASE_URL):
        raise SystemExit("Faltam IG_USER_ID, IG_TOKEN ou BASE_URL.")
    erros = 0
    for r in devidos:
        arqs = r["arquivos"].split("|")
        print(f"[{r['id']}] {r['data']} {r['horario']} {r['tipo']}: {r['frase']}")
        if SIMULAR:
            print(f"   [simulação] {len(arqs)} arquivo(s): {BASE_URL or '<BASE_URL>'}/{arqs[0]}")
            continue
        try:
            media_id = FUNCOES[r["tipo"]](arqs, r["legenda"])
        except SystemExit as e:  # um erro (ex.: reel de teste recusado) não pode travar as outras publicações
            print(f"   ERRO em {r['id']}: {e}")
            erros += 1
            if r["tipo"] == "reel_teste":  # o reel de teste depende de um recurso novo da API: se for recusado, não insistir a cada 2 min
                with open(f"{AQUI}/{r['_log']}", "a", encoding="utf-8") as f:
                    f.write(f"{r['id']};{r['data']};{r['tipo']};ERRO-nao-repetir\n")
            continue
        print(f"   publicado: {media_id}")
        with open(f"{AQUI}/{r['_log']}", "a", encoding="utf-8") as f:
            f.write(f"{r['id']};{r['data']};{r['tipo']};{media_id}\n")
    if erros:
        raise SystemExit(f"{erros} publicação(ões) com erro; as demais seguiram normalmente.")


if __name__ == "__main__":
    main()
