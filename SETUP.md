# Setup (ek baar)

1. GitHub par naya **public** repo banao, naam bilkul `aasif-md1`.
2. Zip extract karo aur saari files repo ke `main` branch mein daalo. `.github` hidden folder bhi jaana chahiye.

       git clone https://github.com/aasif-md1/aasif-md1.git
       # extract ki hui files is folder mein copy karo
       cd aasif-md1
       git add -A
       git commit -m "add profile readme"
       git push origin main

3. Repo > Settings > Actions > General > Workflow permissions > **Read and write permissions** > Save.
4. Repo > Actions > **Update profile README** > **Run workflow**.
5. Run green hone ke baad profile refresh karo.

## Badalna ho to
- Details: `config.json` edit karke push karo.
- Snake speed: `seconds_per_step` (kam value = tez).
- Photo: `pip install pillow`, phir `python scripts/make_ascii.py nayi-photo.png`, phir `assets` push karo.
- Colors: `scripts/generate.py` mein `THEMES`.

## Dhyaan rahe
- Data har 12 ghante mein update hota hai.
- Stats mein sirf public, non-fork repos ke languages aur commits aate hain.
- Snake contribution calendar khata hai (commits, PRs, issues sab shamil).
