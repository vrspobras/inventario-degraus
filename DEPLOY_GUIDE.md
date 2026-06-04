# 🚀 Deploy no Hugging Face Spaces — via Docker

---

## Estrutura final do repositório GitHub

```
inventario-degraus/
├── dashboard_streamlit.py   ← app principal
├── Dockerfile               ← ← NOVO — obrigatório para Docker
├── requirements.txt
├── README.md                ← header com sdk: docker
├── .gitignore
├── kmz_rodovias.kmz
└── logo-viaraposo-2.png
```

> ❌ Nunca suba `banco.db` — ele é criado automaticamente.

---

## Passo 1 — Suba os arquivos no GitHub

Se ainda não tem o repositório:
1. Acesse https://github.com/new
2. Crie o repositório (ex: `inventario-degraus`)
3. Suba todos os arquivos via **"Add file → Upload files"** ou pelo terminal:

```bash
git init
git add .
git commit -m "primeiro commit"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/inventario-degraus.git
git push -u origin main
```

---

## Passo 2 — Crie uma conta no Hugging Face

1. Acesse https://huggingface.co
2. Clique em **Sign Up**
3. Confirme o e-mail

---

## Passo 3 — Crie o Space

1. Acesse https://huggingface.co/new-space
2. Preencha:
   - **Space name:** `inventario-degraus`
   - **License:** MIT
   - **Select the Space SDK:** escolha **Docker** ← importante!
   - **Space hardware:** CPU basic · FREE ✅
   - **Visibility:** Public
3. Clique em **Create Space**

---

## Passo 4 — Conecte ao GitHub

Dentro do Space criado:

1. Clique na aba **"Files"**
2. Clique nos **três pontos "⋯"** → **"Link to a GitHub repository"**
3. Autorize o HF a acessar seu GitHub
4. Selecione o repositório `inventario-degraus`
5. Branch: `main`

A partir daqui, **todo push no GitHub faz redeploy automático**.

---

## Passo 5 — Upload do KMZ e logo (se forem grandes)

Se o `kmz_rodovias.kmz` for grande (>10 MB), faça upload direto no Space:

1. Na aba **"Files"** do Space
2. **"Add file" → "Upload files"**
3. Sobe `kmz_rodovias.kmz` e `logo-viaraposo-2.png`

---

## Passo 6 — Aguarde o build

1. Vá para a aba **"App"** do Space
2. O HF vai buildar o Docker (~5–10 min na primeira vez)
3. Acompanhe em tempo real na aba **"Logs"**
4. Quando aparecer 🟢 **Running** → app online!

URL do app:
```
https://huggingface.co/spaces/SEU_USUARIO/inventario-degraus
```

---

## ⚠️ Persistência do banco de dados

O container Docker no HF Spaces **reinicia ocasionalmente** e perde o `banco.db`.
Para salvar os dados permanentemente, use um Dataset privado do HF como "disco":

### Configuração (uma vez só)

**1. Crie um Dataset privado:**
- Acesse https://huggingface.co/new-dataset
- Name: `inventario-degraus-db`
- Visibility: **Private**
- Clique em **Create dataset**

**2. Gere um token de acesso:**
- Acesse https://huggingface.co/settings/tokens
- Clique em **New token**
- Nome: `inventario-app`
- Tipo: **Write**
- Copie o token gerado (começa com `hf_...`)

**3. Adicione o token como Secret no Space:**
- No Space, vá em **Settings → Variables and Secrets**
- Clique em **New secret**
- Name: `HF_TOKEN`
- Value: cole o token `hf_...`
- Clique em **Save**

**4. Adicione estas linhas no topo do `dashboard_streamlit.py`**
(logo depois dos imports):

```python
import os, shutil
from huggingface_hub import hf_hub_download, HfApi

HF_TOKEN = os.environ.get("HF_TOKEN", "")
HF_REPO  = "SEU_USUARIO/inventario-degraus-db"  # ← troque pelo seu usuário
DB_FILE  = "banco.db"

# Baixar banco salvo ao iniciar
if HF_TOKEN and not os.path.exists(DB_FILE):
    try:
        path = hf_hub_download(
            repo_id=HF_REPO, filename=DB_FILE,
            repo_type="dataset", token=HF_TOKEN
        )
        shutil.copy(path, DB_FILE)
    except Exception:
        pass  # banco novo se ainda não existir

def sincronizar_banco():
    """Chame após cada commit no banco para persistir no HF Dataset."""
    if not HF_TOKEN:
        return
    try:
        HfApi().upload_file(
            path_or_fileobj=DB_FILE, path_in_repo=DB_FILE,
            repo_id=HF_REPO, repo_type="dataset", token=HF_TOKEN
        )
    except Exception as e:
        print(f"Erro ao sincronizar banco: {e}")
```

**5. Chame `sincronizar_banco()` após cada `con.commit()` nas funções de salvar e apagar.**

---

## 🔄 Atualizando o app no futuro

Qualquer alteração no código → push no GitHub → redeploy automático:

```bash
git add dashboard_streamlit.py
git commit -m "melhoria no dashboard"
git push
```

---

## 📋 Checklist final

| Arquivo                  | GitHub | HF Space direto |
|--------------------------|--------|-----------------|
| `dashboard_streamlit.py` | ✅     |                 |
| `Dockerfile`             | ✅     |                 |
| `requirements.txt`       | ✅     |                 |
| `README.md`              | ✅     |                 |
| `.gitignore`             | ✅     |                 |
| `kmz_rodovias.kmz`       | ✅ ou  | ✅ upload direto|
| `logo-viaraposo-2.png`   | ✅ ou  | ✅ upload direto|
| `banco.db`               | ❌ nunca subir  |       |
