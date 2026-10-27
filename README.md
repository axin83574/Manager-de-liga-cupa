# Manager Liga de Fotbal — Streamlit

## Pregătire Supabase
1. Deschide proiectul Supabase și rulează o singură dată `supabase_schema.sql` din SQL Editor.
2. În `.streamlit/secrets.toml` completează `SUPABASE_URL` și cheia server-side `SUPABASE_SERVICE_ROLE_KEY`.
3. Nu publica și nu trimite cheia service role. Fișierul `secrets.toml` este exclus din Git.

## Importul datelor existente
Cu Python instalat, din acest folder rulează:

```powershell
python migrate_liga_baza_to_supabase.py "C:\Users\user\Desktop\liga fotbal\liga_baza.json"
```

Scriptul importă conturile și ligile în tabelele private `app_users` și `app_leagues`, face copie de siguranță a conținutului existent din aceste tabele și nu importă sesiunea activă. Tabela veche `public.ligi` nu este ștearsă.

## Pornire locală

```powershell
python -m streamlit run streamlit_app.py
```

Pentru Streamlit Community Cloud, publică fișierele acestui folder într-un repository GitHub, selectează `streamlit_app.py` și completează aceleași două secrete în setările aplicației Streamlit Cloud.
