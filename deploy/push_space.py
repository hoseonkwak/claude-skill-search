#!/usr/bin/env python3
"""
Deploy the Skill Finder app to a Hugging Face Space (Docker).
Assembles Dockerfile + requirements + README + scripts + data into a temp
folder and uploads it. Large files (embeddings.npy) go via LFS automatically.

Auth: <project>/.hf_token  (HF write token). Usage: push_space.py <hf_user> [space_name]
"""
import shutil
import sys
import tempfile
from pathlib import Path

from huggingface_hub import HfApi, create_repo

ROOT = Path(__file__).resolve().parent.parent
USER = sys.argv[1]
SPACE = sys.argv[2] if len(sys.argv) > 2 else "skill-finder"
TOKEN = (ROOT / ".hf_token").read_text(encoding="utf-8").strip()

DATA_FILES = ["skills.json", "embed_meta.json", "embeddings.npy",
              "stars.json", "safety.json", "collections.json"]
SCRIPTS = ["core.py", "serve.py", "ui.py"]

d = Path(tempfile.mkdtemp())
for f in ("Dockerfile", "requirements.txt", "README.md"):
    shutil.copy(ROOT / "deploy" / f, d / f)
(d / "scripts").mkdir()
(d / "data").mkdir()
for f in SCRIPTS:
    shutil.copy(ROOT / "scripts" / f, d / "scripts" / f)
for f in DATA_FILES:
    shutil.copy(ROOT / "data" / f, d / "data" / f)

repo_id = f"{USER}/{SPACE}"
print(f"creating/using space {repo_id} ...", flush=True)
create_repo(repo_id, repo_type="space", space_sdk="docker", exist_ok=True, token=TOKEN)
print("uploading (this includes embeddings.npy via LFS) ...", flush=True)
HfApi(token=TOKEN).upload_folder(folder_path=str(d), repo_id=repo_id, repo_type="space",
                                 commit_message="deploy skill-finder")
app = f"https://{USER.lower().replace('_', '-')}-{SPACE.lower()}.hf.space"
print("\nSpace:", f"https://huggingface.co/spaces/{repo_id}")
print("App  :", app, "(builds in ~2-5 min)")
