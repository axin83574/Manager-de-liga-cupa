# GolStat — aplicație de management pentru ligi de fotbal

Logo-ul aplicației este în `golstat_logo.png`; păstrează acest fișier în rădăcina repository-ului când publici actualizările.

## Pregătire Supabase
1. Deschide proiectul Supabase și rulează o singură dată `supabase_schema.sql` din SQL Editor.
2. În `.streamlit/secrets.toml` completează `SUPABASE_URL` și cheia server-side `SUPABASE_SERVICE_ROLE_KEY`. Opțional, setează `APP_PUBLIC_URL` pentru linkurile și codurile QR de acces.
3. Nu publica și nu trimite cheia service role. Fișierul `secrets.toml` este exclus din Git.

## Suportul aplicației
1. Rulează din nou `supabase_schema.sql` în Supabase SQL Editor pentru a crea tabela privată `app_support_messages`.
2. În Secrets, setează `SUPPORT_ADMIN_USERNAME` la numele contului aplicației care trebuie să primească mesajele.
3. Utilizatorii pot trimite buguri, cereri de modificare sau întrebări din butonul „Suportul aplicației”, chiar dacă nu au intrat într-o ligă. Mesajele și adresele pentru răspuns sunt vizibile doar contului de suport.

## Recuperarea parolei
1. Rulează din nou `supabase_schema.sql` în Supabase SQL Editor pentru a crea tabela privată `app_password_resets`.
2. Configurează un cont Resend și verifică un domeniu de trimitere. În Streamlit Cloud → App settings → Secrets adaugă `RESEND_API_KEY`, `PASSWORD_RESET_FROM_EMAIL` (de forma `GolStat <noreply@domeniul-tau.ro>`) și `APP_PUBLIC_URL` cu adresa publică a aplicației.
3. Linkurile sunt de unică folosință, expiră în 30 de minute, iar aplicația limitează cererile repetate. La resetare sunt revocate și sesiunile persistente ale contului.

## Plată pentru crearea ligilor
Crearea unei competiții este procesată prin Stripe Checkout: Cupă — 0,50 €, Ligă — 0,75 €, Ligă + cupă — 1,00 €. Suma este stabilită pe server și verificată înainte ca aplicația să creeze liga.

1. Creează/activează un cont Stripe și începe cu cheile de test din Stripe Dashboard.
2. În Streamlit Cloud → App settings → Secrets adaugă `STRIPE_SECRET_KEY = "sk_test_..."`. Pentru plata reală, după ce verifici fluxul în test mode, înlocuiește cu cheia `sk_live_...`.
3. Configurează și `APP_PUBLIC_URL` cu URL-ul public al aplicației, plus Supabase (`SUPABASE_URL` și `SUPABASE_SERVICE_ROLE_KEY`).

Nu pune cheia Stripe în cod sau în GitHub. Stripe procesează Checkout-ul; liga se creează doar după ce aplicația verifică o sesiune plătită, pentru contul și suma corecte.

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

Pentru Streamlit Community Cloud, publică fișierele acestui folder într-un repository GitHub, selectează `streamlit_app.py` și completează `SUPABASE_URL` și `SUPABASE_SERVICE_ROLE_KEY` în setările aplicației Streamlit Cloud. Pentru QR/linkuri, adaugă și `APP_PUBLIC_URL` cu adresa publică a aplicației.
