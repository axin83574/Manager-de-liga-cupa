"""Manager de ligă Streamlit, cu stocare Supabase și fallback local pentru dezvoltare."""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import shutil
import uuid
from pathlib import Path

import streamlit as st
import extra_streamlit_components as stx
from supabase import create_client


STATS_ECHIPA = {"meciuri_jucate": 0, "goluri_marcate": 0,
                "goluri_primite": 0, "puncte": 0}
STATS_JUCATOR = {"goluri": 0, "asisturi": 0,
                 "cartonase_galbene": 0, "cartonase_rosii": 0}
POZITII_FOTBAL = (
    "Portar", "Portar (GK)", "Fundaș", "Fundaș central (CB)",
    "Fundaș dreapta (RB)", "Fundaș stânga (LB)",
    "Fundaș dreapta avansat (RWB)", "Fundaș stânga avansat (LWB)",
    "Mijlocaș defensiv (CDM)", "Mijlocaș central (CM)",
    "Mijlocaș ofensiv (CAM)", "Mijlocaș dreapta (RM)",
    "Mijlocaș stânga (LM)", "Extremă dreapta (RW)",
    "Extremă stânga (LW)", "Atacant central (CF)", "Vârf (ST)",
    "Mijlocaș", "Atacant", "Toate posturile", "Tot ca jucător de câmp",
)
TIPURI_GOL = ("Gol Normal", "Gol din Lovitură Liberă", "Penalty")
TIPURI_EVENIMENT = TIPURI_GOL + ("Autogol", "Penalty Ratat",
                                 "Cartonaș Galben", "Cartonaș Roșu", "Schimbare")
LANGUAGE_OPTIONS = {"Română": "ro", "English": "en", "Français": "fr", "Español": "es"}
UI_TRANSLATIONS = {
    "en": {
        "Limba": "Language", "Profilul meu": "My profile", "Jucătorul meu": "My player",
        "Deconectare": "Log out", "Schimbă liga": "Change league", "Navigare": "Navigation",
        "Intră în cont sau creează un profil": "Sign in or create an account",
        "Te poți conecta cu numele de utilizator sau adresa de e-mail asociată contului.": "Sign in with your username or the email address linked to your account.",
        "Autentificare": "Sign in", "Cont nou": "Create account", "Nume de utilizator sau e-mail": "Username or email",
        "Nume de utilizator": "Username", "Parolă": "Password", "Intră în cont": "Sign in",
        "Rămâi conectat pe acest dispozitiv (30 de zile)": "Stay signed in on this device (30 days)",
        "Profilul rămâne disponibil indiferent de liga deschisă.": "Your profile is available no matter which league is open.",
        "Datele contului": "Account details", "Schimbă parola": "Change password",
        "Asocierea cu jucătorii din ligile tale": "Link your player in each league",
        "Salvează asocierea": "Save player selection", "Statisticile mele": "My statistics",
        "Meciuri jucate": "Played matches", "Urmează": "Upcoming", "Live": "Live",
        "Trofee": "Trophies", "Echipele mele": "My teams", "Goluri": "Goals",
        "Assisturi": "Assists", "Cartonașe galbene": "Yellow cards", "Cartonașe roșii": "Red cards",
        "Omul meciului": "Player of the match", "Pe fiecare ligă": "By league",
        "Trofee câștigate": "Trophies won", "Ligă": "League", "Echipă": "Team",
        "Jucător": "Player", "Etapa": "Round", "Competiție": "Competition", "Data": "Date", "Meci": "Match",
        "Echipă aleasă": "Selected team", "Jucător ales": "Selected player",
        "Echipă actuală după transferuri": "Current team after transfers",
        "Asociază-ți un jucător în cel puțin o ligă din secțiunea de mai sus. Aici apar doar ligile în care ai ales un jucător.":
            "Link yourself to a player in at least one league above. Only leagues where you selected a player appear here.",
        "Intră în ligă": "Join a league", "Creează o ligă": "Create a league",
        "Bine ai venit în Managerul Ligii de Fotbal": "Welcome to Football League Manager",
        "Creează o ligă nouă sau intră într-o ligă pe care o administrezi ori care ți-a fost partajată.":
            "Create a league or join one you manage or that has been shared with you.",
        "Administrează ligile mele": "Manage my leagues", "Alege liga": "Choose a league",
        "Importă o ligă existentă": "Import an existing league", "Continuă cu codul": "Continue with code",
        "Clasament": "Standings", "Statistici": "Statistics", "Echipe și jucători": "Teams and players",
        "Meciuri și program": "Matches and schedule", "Arbitraj": "Refereeing", "Cupa": "Cup",
        "Supercupa": "Super Cup", "Premii sezon": "Season awards", "Transferuri": "Transfers",
        "Membri": "Members", "Import / export": "Import / export", "Setări ligă": "League settings",
        "Înapoi la aplicație": "Back to the app", "Numele ligii": "League name",
        "Creează liga": "Create league", "Ligă goală": "Empty league", "Tipul competiției": "Competition type",
        "Adresă de e-mail": "Email address", "Nume și prenume": "Full name",
        "Confirmă parola": "Confirm password", "Parolă (minimum 6 caractere)": "Password (at least 6 characters)",
        "Joci la un club profesionist?": "Do you play for a professional club?", "Poziția ta": "Your position",
        "Salvează profilul": "Save profile", "Echipa": "Team", "Deschide": "Open",
        "Alegeri de profil și administrare ligi": "Player selection and league management",
        "Câștigat ca": "Won as", "Proprietar": "Owner", "Galbene": "Yellow cards", "Roșii": "Red cards",
        "Liga": "League", "Administrare ligi": "League management", "Salvează alegerea": "Save selection",
        "Numele de utilizator sau parola nu corespund.": "The username or password is incorrect.",
        "Statistici": "Statistics", "În desfășurare": "In progress", "Nesetată": "Not set",
    },
    "es": {
        "Limba": "Idioma", "Profilul meu": "Mi perfil", "Jucătorul meu": "Mi jugador",
        "Deconectare": "Cerrar sesión", "Schimbă liga": "Cambiar de liga", "Navigare": "Navegación",
        "Intră în cont sau creează un profil": "Inicia sesión o crea una cuenta",
        "Te poți conecta cu numele de utilizator sau adresa de e-mail asociată contului.": "Inicia sesión con tu nombre de usuario o el correo asociado a tu cuenta.",
        "Autentificare": "Iniciar sesión", "Cont nou": "Crear cuenta", "Nume de utilizator sau e-mail": "Usuario o correo electrónico",
        "Nume de utilizator": "Nombre de usuario", "Parolă": "Contraseña", "Intră în cont": "Iniciar sesión",
        "Rămâi conectat pe acest dispozitiv (30 de zile)": "Mantener la sesión en este dispositivo (30 días)",
        "Profilul rămâne disponibil indiferent de liga deschisă.": "Tu perfil está disponible independientemente de la liga abierta.",
        "Datele contului": "Datos de la cuenta", "Schimbă parola": "Cambiar contraseña",
        "Asocierea cu jucătorii din ligile tale": "Vincula tu jugador en cada liga",
        "Salvează asocierea": "Guardar selección de jugador", "Statisticile mele": "Mis estadísticas",
        "Meciuri jucate": "Partidos jugados", "Urmează": "Próximos", "Live": "En directo",
        "Trofee": "Trofeos", "Echipele mele": "Mis equipos", "Goluri": "Goles",
        "Assisturi": "Asistencias", "Cartonașe galbene": "Tarjetas amarillas", "Cartonașe roșii": "Tarjetas rojas",
        "Omul meciului": "Jugador del partido", "Pe fiecare ligă": "Por liga",
        "Trofee câștigate": "Trofeos ganados", "Ligă": "Liga", "Echipă": "Equipo",
        "Jucător": "Jugador", "Etapa": "Jornada", "Competiție": "Competición", "Data": "Fecha", "Meci": "Partido",
        "Echipă aleasă": "Equipo seleccionado", "Jucător ales": "Jugador seleccionado",
        "Echipă actuală după transferuri": "Equipo actual tras los traspasos",
        "Asociază-ți un jucător în cel puțin o ligă din secțiunea de mai sus. Aici apar doar ligile în care ai ales un jucător.":
            "Vincúlate a un jugador en al menos una liga de arriba. Aquí solo aparecen las ligas donde elegiste un jugador.",
        "Intră în ligă": "Entrar en una liga", "Creează o ligă": "Crear una liga",
        "Bine ai venit în Managerul Ligii de Fotbal": "Bienvenido al Gestor de Ligas de Fútbol",
        "Creează o ligă nouă sau intră într-o ligă pe care o administrezi ori care ți-a fost partajată.":
            "Crea una liga o únete a una que administres o que hayan compartido contigo.",
        "Administrează ligile mele": "Gestionar mis ligas", "Alege liga": "Elige una liga",
        "Importă o ligă existentă": "Importar una liga existente", "Continuă cu codul": "Continuar con código",
        "Clasament": "Clasificación", "Statistici": "Estadísticas", "Echipe și jucători": "Equipos y jugadores",
        "Meciuri și program": "Partidos y calendario", "Arbitraj": "Arbitraje", "Cupa": "Copa",
        "Supercupa": "Supercopa", "Premii sezon": "Premios de temporada", "Transferuri": "Traspasos",
        "Membri": "Miembros", "Import / export": "Importar / exportar", "Setări ligă": "Configuración de liga",
        "Înapoi la aplicație": "Volver a la aplicación", "Numele ligii": "Nombre de la liga",
        "Creează liga": "Crear liga", "Ligă goală": "Liga vacía", "Tipul competiției": "Tipo de competición",
        "Adresă de e-mail": "Correo electrónico", "Nume și prenume": "Nombre completo",
        "Confirmă parola": "Confirmar contraseña", "Parolă (minimum 6 caractere)": "Contraseña (mínimo 6 caracteres)",
        "Joci la un club profesionist?": "¿Juegas en un club profesional?", "Poziția ta": "Tu posición",
        "Salvează profilul": "Guardar perfil", "Echipa": "Equipo", "Deschide": "Abrir",
        "Câștigat ca": "Ganado como", "Proprietar": "Propietario", "Galbene": "Amarillas", "Roșii": "Rojas",
        "Liga": "Liga", "Administrare ligi": "Gestión de ligas", "Salvează alegerea": "Guardar selección",
        "Statistici": "Estadísticas", "În desfășurare": "En curso", "Nesetată": "Sin fecha",
    },
}

UI_TRANSLATIONS.update({
    "zh": {
        "Limba": "语言", "Profilul meu": "我的个人资料", "Jucătorul meu": "我的球员", "Deconectare": "退出登录",
        "Schimbă liga": "切换联赛", "Navigare": "导航", "Autentificare": "登录", "Cont nou": "创建账户",
        "Nume de utilizator sau e-mail": "用户名或邮箱", "Parolă": "密码", "Intră în cont": "登录",
        "Statisticile mele": "我的统计", "Meciuri jucate": "已进行的比赛", "Urmează": "即将进行", "Live": "直播",
        "Trofee": "奖杯", "Echipele mele": "我的球队", "Goluri": "进球", "Assisturi": "助攻",
        "Cartonașe galbene": "黄牌", "Cartonașe roșii": "红牌", "Omul meciului": "全场最佳球员",
        "Pe fiecare ligă": "各联赛统计", "Trofee câștigate": "获得的奖杯", "Ligă": "联赛", "Echipă": "球队",
        "Jucător": "球员", "Etapa": "轮次", "Competiție": "赛事", "Data": "日期", "Meci": "比赛",
        "Intră în ligă": "加入联赛", "Creează o ligă": "创建联赛", "Clasament": "排名", "Statistici": "统计",
        "Echipe și jucători": "球队和球员", "Meciuri și program": "比赛和赛程", "Arbitraj": "裁判", "Cupa": "杯赛",
        "Supercupa": "超级杯", "Premii sezon": "赛季奖项", "Transferuri": "转会", "Membri": "成员",
        "Import / export": "导入 / 导出", "Setări ligă": "联赛设置", "Bine ai venit în Managerul Ligii de Fotbal": "欢迎使用足球联赛管理器",
        "Numele ligii": "联赛名称", "Creează liga": "创建联赛", "Tipul competiției": "赛事类型",
    },
    "hi": {
        "Limba": "भाषा", "Profilul meu": "मेरी प्रोफ़ाइल", "Jucătorul meu": "मेरा खिलाड़ी", "Deconectare": "लॉग आउट",
        "Schimbă liga": "लीग बदलें", "Navigare": "नेविगेशन", "Autentificare": "लॉग इन", "Cont nou": "नया खाता",
        "Nume de utilizator sau e-mail": "उपयोगकर्ता नाम या ईमेल", "Parolă": "पासवर्ड", "Intră în cont": "लॉग इन करें",
        "Statisticile mele": "मेरे आँकड़े", "Meciuri jucate": "खेले गए मैच", "Urmează": "आगामी", "Live": "लाइव",
        "Trofee": "ट्रॉफ़ियाँ", "Echipele mele": "मेरी टीमें", "Goluri": "गोल", "Assisturi": "असिस्ट",
        "Cartonașe galbene": "पीले कार्ड", "Cartonașe roșii": "लाल कार्ड", "Omul meciului": "मैच का सर्वश्रेष्ठ खिलाड़ी",
        "Pe fiecare ligă": "हर लीग के आँकड़े", "Trofee câștigate": "जीती गई ट्रॉफ़ियाँ", "Ligă": "लीग", "Echipă": "टीम",
        "Jucător": "खिलाड़ी", "Etapa": "राउंड", "Competiție": "प्रतियोगिता", "Data": "तारीख", "Meci": "मैच",
        "Intră în ligă": "लीग में शामिल हों", "Creează o ligă": "लीग बनाएँ", "Clasament": "तालिका", "Statistici": "आँकड़े",
        "Echipe și jucători": "टीमें और खिलाड़ी", "Meciuri și program": "मैच और कार्यक्रम", "Arbitraj": "रेफ़री", "Cupa": "कप",
        "Supercupa": "सुपर कप", "Premii sezon": "सीज़न पुरस्कार", "Transferuri": "ट्रांसफ़र", "Membri": "सदस्य",
        "Import / export": "आयात / निर्यात", "Setări ligă": "लीग सेटिंग्स", "Bine ai venit în Managerul Ligii de Fotbal": "फुटबॉल लीग मैनेजर में आपका स्वागत है",
        "Numele ligii": "लीग का नाम", "Creează liga": "लीग बनाएँ", "Tipul competiției": "प्रतियोगिता का प्रकार",
    },
    "fr": {
        "Limba": "Langue", "Profilul meu": "Mon profil", "Jucătorul meu": "Mon joueur", "Deconectare": "Déconnexion",
        "Schimbă liga": "Changer de ligue", "Navigare": "Navigation", "Autentificare": "Connexion", "Cont nou": "Nouveau compte",
        "Nume de utilizator sau e-mail": "Nom d’utilisateur ou e-mail", "Parolă": "Mot de passe", "Intră în cont": "Se connecter",
        "Statisticile mele": "Mes statistiques", "Meciuri jucate": "Matchs joués", "Urmează": "À venir", "Live": "En direct",
        "Trofee": "Trophées", "Echipele mele": "Mes équipes", "Goluri": "Buts", "Assisturi": "Passes décisives",
        "Cartonașe galbene": "Cartons jaunes", "Cartonașe roșii": "Cartons rouges", "Omul meciului": "Joueur du match",
        "Pe fiecare ligă": "Par ligue", "Trofee câștigate": "Trophées remportés", "Ligă": "Ligue", "Echipă": "Équipe",
        "Jucător": "Joueur", "Etapa": "Journée", "Competiție": "Compétition", "Data": "Date", "Meci": "Match",
        "Intră în ligă": "Rejoindre une ligue", "Creează o ligă": "Créer une ligue", "Clasament": "Classement", "Statistici": "Statistiques",
        "Echipe și jucători": "Équipes et joueurs", "Meciuri și program": "Matchs et calendrier", "Arbitraj": "Arbitrage", "Cupa": "Coupe",
        "Supercupa": "Supercoupe", "Premii sezon": "Prix de la saison", "Transferuri": "Transferts", "Membri": "Membres",
        "Import / export": "Importer / exporter", "Setări ligă": "Paramètres de la ligue", "Bine ai venit în Managerul Ligii de Fotbal": "Bienvenue dans le gestionnaire de ligue de football",
        "Numele ligii": "Nom de la ligue", "Creează liga": "Créer la ligue", "Tipul competiției": "Type de compétition",
    },
    "bn": {
        "Limba": "ভাষা", "Profilul meu": "আমার প্রোফাইল", "Jucătorul meu": "আমার খেলোয়াড়", "Deconectare": "লগ আউট",
        "Schimbă liga": "লিগ পরিবর্তন", "Navigare": "নেভিগেশন", "Autentificare": "লগ ইন", "Cont nou": "নতুন অ্যাকাউন্ট",
        "Nume de utilizator sau e-mail": "ব্যবহারকারীর নাম বা ইমেল", "Parolă": "পাসওয়ার্ড", "Intră în cont": "লগ ইন করুন",
        "Statisticile mele": "আমার পরিসংখ্যান", "Meciuri jucate": "খেলা ম্যাচ", "Urmează": "আসন্ন", "Live": "লাইভ",
        "Trofee": "ট্রফি", "Echipele mele": "আমার দল", "Goluri": "গোল", "Assisturi": "অ্যাসিস্ট",
        "Cartonașe galbene": "হলুদ কার্ড", "Cartonașe roșii": "লাল কার্ড", "Omul meciului": "ম্যাচসেরা খেলোয়াড়",
        "Pe fiecare ligă": "প্রতি লিগে", "Trofee câștigate": "জেতা ট্রফি", "Ligă": "লিগ", "Echipă": "দল",
        "Jucător": "খেলোয়াড়", "Etapa": "রাউন্ড", "Competiție": "প্রতিযোগিতা", "Data": "তারিখ", "Meci": "ম্যাচ",
        "Intră în ligă": "লিগে যোগ দিন", "Creează o ligă": "লিগ তৈরি করুন", "Clasament": "লিগ টেবিল", "Statistici": "পরিসংখ্যান",
        "Echipe și jucători": "দল ও খেলোয়াড়", "Meciuri și program": "ম্যাচ ও সূচি", "Arbitraj": "রেফারি", "Cupa": "কাপ",
        "Supercupa": "সুপার কাপ", "Premii sezon": "মৌসুমের পুরস্কার", "Transferuri": "ট্রান্সফার", "Membri": "সদস্য",
        "Import / export": "ইমপোর্ট / এক্সপোর্ট", "Setări ligă": "লিগ সেটিংস", "Bine ai venit în Managerul Ligii de Fotbal": "ফুটবল লিগ ম্যানেজারে স্বাগতম",
        "Numele ligii": "লিগের নাম", "Creează liga": "লিগ তৈরি করুন", "Tipul competiției": "প্রতিযোগিতার ধরন",
    },
    "pt": {
        "Limba": "Idioma", "Profilul meu": "Meu perfil", "Jucătorul meu": "Meu jogador", "Deconectare": "Sair",
        "Schimbă liga": "Trocar de liga", "Navigare": "Navegação", "Autentificare": "Entrar", "Cont nou": "Nova conta",
        "Nume de utilizator sau e-mail": "Usuário ou e-mail", "Parolă": "Senha", "Intră în cont": "Entrar",
        "Statisticile mele": "Minhas estatísticas", "Meciuri jucate": "Partidas disputadas", "Urmează": "Próximas", "Live": "Ao vivo",
        "Trofee": "Troféus", "Echipele mele": "Meus times", "Goluri": "Gols", "Assisturi": "Assistências",
        "Cartonașe galbene": "Cartões amarelos", "Cartonașe roșii": "Cartões vermelhos", "Omul meciului": "Melhor jogador da partida",
        "Pe fiecare ligă": "Por liga", "Trofee câștigate": "Troféus conquistados", "Ligă": "Liga", "Echipă": "Time",
        "Jucător": "Jogador", "Etapa": "Rodada", "Competiție": "Competição", "Data": "Data", "Meci": "Partida",
        "Intră în ligă": "Entrar em uma liga", "Creează o ligă": "Criar uma liga", "Clasament": "Classificação", "Statistici": "Estatísticas",
        "Echipe și jucători": "Times e jogadores", "Meciuri și program": "Partidas e calendário", "Arbitraj": "Arbitragem", "Cupa": "Copa",
        "Supercupa": "Supercopa", "Premii sezon": "Prêmios da temporada", "Transferuri": "Transferências", "Membri": "Membros",
        "Import / export": "Importar / exportar", "Setări ligă": "Configurações da liga", "Bine ai venit în Managerul Ligii de Fotbal": "Bem-vindo ao Gerenciador de Ligas de Futebol",
        "Numele ligii": "Nome da liga", "Creează liga": "Criar liga", "Tipul competiției": "Tipo de competição",
    },
    "id": {
        "Limba": "Bahasa", "Profilul meu": "Profil saya", "Jucătorul meu": "Pemain saya", "Deconectare": "Keluar",
        "Schimbă liga": "Ganti liga", "Navigare": "Navigasi", "Autentificare": "Masuk", "Cont nou": "Akun baru",
        "Nume de utilizator sau e-mail": "Nama pengguna atau email", "Parolă": "Kata sandi", "Intră în cont": "Masuk",
        "Statisticile mele": "Statistik saya", "Meciuri jucate": "Pertandingan dimainkan", "Urmează": "Jadwal berikutnya", "Live": "Langsung",
        "Trofee": "Trofi", "Echipele mele": "Tim saya", "Goluri": "Gol", "Assisturi": "Assist",
        "Cartonașe galbene": "Kartu kuning", "Cartonașe roșii": "Kartu merah", "Omul meciului": "Pemain terbaik pertandingan",
        "Pe fiecare ligă": "Per liga", "Trofee câștigate": "Trofi yang dimenangkan", "Ligă": "Liga", "Echipă": "Tim",
        "Jucător": "Pemain", "Etapa": "Babak", "Competiție": "Kompetisi", "Data": "Tanggal", "Meci": "Pertandingan",
        "Intră în ligă": "Gabung liga", "Creează o ligă": "Buat liga", "Clasament": "Klasemen", "Statistici": "Statistik",
        "Echipe și jucători": "Tim dan pemain", "Meciuri și program": "Pertandingan dan jadwal", "Arbitraj": "Wasit", "Cupa": "Piala",
        "Supercupa": "Piala Super", "Premii sezon": "Penghargaan musim", "Transferuri": "Transfer", "Membri": "Anggota",
        "Import / export": "Impor / ekspor", "Setări ligă": "Pengaturan liga", "Bine ai venit în Managerul Ligii de Fotbal": "Selamat datang di Manajer Liga Sepak Bola",
        "Numele ligii": "Nama liga", "Creează liga": "Buat liga", "Tipul competiției": "Jenis kompetisi",
    },
    "ru": {
        "Limba": "Язык", "Profilul meu": "Мой профиль", "Jucătorul meu": "Мой игрок", "Deconectare": "Выйти",
        "Schimbă liga": "Сменить лигу", "Navigare": "Навигация", "Autentificare": "Вход", "Cont nou": "Новый аккаунт",
        "Nume de utilizator sau e-mail": "Имя пользователя или эл. почта", "Parolă": "Пароль", "Intră în cont": "Войти",
        "Statisticile mele": "Моя статистика", "Meciuri jucate": "Сыгранные матчи", "Urmează": "Предстоящие", "Live": "В эфире",
        "Trofee": "Трофеи", "Echipele mele": "Мои команды", "Goluri": "Голы", "Assisturi": "Голевые передачи",
        "Cartonașe galbene": "Жёлтые карточки", "Cartonașe roșii": "Красные карточки", "Omul meciului": "Лучший игрок матча",
        "Pe fiecare ligă": "По каждой лиге", "Trofee câștigate": "Выигранные трофеи", "Ligă": "Лига", "Echipă": "Команда",
        "Jucător": "Игрок", "Etapa": "Тур", "Competiție": "Соревнование", "Data": "Дата", "Meci": "Матч",
        "Intră în ligă": "Войти в лигу", "Creează o ligă": "Создать лигу", "Clasament": "Таблица", "Statistici": "Статистика",
        "Echipe și jucători": "Команды и игроки", "Meciuri și program": "Матчи и расписание", "Arbitraj": "Судейство", "Cupa": "Кубок",
        "Supercupa": "Суперкубок", "Premii sezon": "Награды сезона", "Transferuri": "Трансферы", "Membri": "Участники",
        "Import / export": "Импорт / экспорт", "Setări ligă": "Настройки лиги", "Bine ai venit în Managerul Ligii de Fotbal": "Добро пожаловать в менеджер футбольной лиги",
        "Numele ligii": "Название лиги", "Creează liga": "Создать лигу", "Tipul competiției": "Тип соревнования",
    },
    "de": {
        "Limba": "Sprache", "Profilul meu": "Mein Profil", "Jucătorul meu": "Mein Spieler", "Deconectare": "Abmelden",
        "Schimbă liga": "Liga wechseln", "Navigare": "Navigation", "Autentificare": "Anmelden", "Cont nou": "Neues Konto",
        "Nume de utilizator sau e-mail": "Benutzername oder E-Mail", "Parolă": "Passwort", "Intră în cont": "Anmelden",
        "Statisticile mele": "Meine Statistiken", "Meciuri jucate": "Gespielte Spiele", "Urmează": "Anstehend", "Live": "Live",
        "Trofee": "Pokale", "Echipele mele": "Meine Teams", "Goluri": "Tore", "Assisturi": "Vorlagen",
        "Cartonașe galbene": "Gelbe Karten", "Cartonașe roșii": "Rote Karten", "Omul meciului": "Spieler des Spiels",
        "Pe fiecare ligă": "Nach Liga", "Trofee câștigate": "Gewonnene Pokale", "Ligă": "Liga", "Echipă": "Mannschaft",
        "Jucător": "Spieler", "Etapa": "Spieltag", "Competiție": "Wettbewerb", "Data": "Datum", "Meci": "Spiel",
        "Intră în ligă": "Liga beitreten", "Creează o ligă": "Liga erstellen", "Clasament": "Tabelle", "Statistici": "Statistiken",
        "Echipe și jucători": "Teams und Spieler", "Meciuri și program": "Spiele und Spielplan", "Arbitraj": "Schiedsrichter", "Cupa": "Pokal",
        "Supercupa": "Superpokal", "Premii sezon": "Saisonauszeichnungen", "Transferuri": "Transfers", "Membri": "Mitglieder",
        "Import / export": "Import / Export", "Setări ligă": "Ligaeinstellungen", "Bine ai venit în Managerul Ligii de Fotbal": "Willkommen beim Fußball-Liga-Manager",
        "Numele ligii": "Liga-Name", "Creează liga": "Liga erstellen", "Tipul competiției": "Wettbewerbstyp",
    },
    "ja": {
        "Limba": "言語", "Profilul meu": "プロフィール", "Jucătorul meu": "マイ選手", "Deconectare": "ログアウト",
        "Schimbă liga": "リーグを変更", "Navigare": "ナビゲーション", "Autentificare": "ログイン", "Cont nou": "新しいアカウント",
        "Nume de utilizator sau e-mail": "ユーザー名またはメール", "Parolă": "パスワード", "Intră în cont": "ログイン",
        "Statisticile mele": "自分の成績", "Meciuri jucate": "出場試合", "Urmează": "今後の試合", "Live": "ライブ",
        "Trofee": "トロフィー", "Echipele mele": "所属チーム", "Goluri": "ゴール", "Assisturi": "アシスト",
        "Cartonașe galbene": "イエローカード", "Cartonașe roșii": "レッドカード", "Omul meciului": "マン・オブ・ザ・マッチ",
        "Pe fiecare ligă": "リーグ別", "Trofee câștigate": "獲得トロフィー", "Ligă": "リーグ", "Echipă": "チーム",
        "Jucător": "選手", "Etapa": "節", "Competiție": "大会", "Data": "日付", "Meci": "試合",
        "Intră în ligă": "リーグに参加", "Creează o ligă": "リーグを作成", "Clasament": "順位表", "Statistici": "統計",
        "Echipe și jucători": "チームと選手", "Meciuri și program": "試合と日程", "Arbitraj": "審判", "Cupa": "カップ戦",
        "Supercupa": "スーパーカップ", "Premii sezon": "シーズン表彰", "Transferuri": "移籍", "Membri": "メンバー",
        "Import / export": "インポート / エクスポート", "Setări ligă": "リーグ設定", "Bine ai venit în Managerul Ligii de Fotbal": "サッカーリーグ管理へようこそ",
        "Numele ligii": "リーグ名", "Creează liga": "リーグを作成", "Tipul competiției": "大会形式",
    },
    "ar": {
        "Limba": "اللغة", "Profilul meu": "ملفي الشخصي", "Jucătorul meu": "لاعبي", "Deconectare": "تسجيل الخروج",
        "Schimbă liga": "تغيير الدوري", "Navigare": "التنقل", "Autentificare": "تسجيل الدخول", "Cont nou": "حساب جديد",
        "Nume de utilizator sau e-mail": "اسم المستخدم أو البريد الإلكتروني", "Parolă": "كلمة المرور", "Intră în cont": "دخول",
        "Statisticile mele": "إحصائياتي", "Meciuri jucate": "المباريات التي لعبتها", "Urmează": "المباريات القادمة", "Live": "مباشر",
        "Trofee": "الكؤوس", "Echipele mele": "فرقي", "Goluri": "أهداف", "Assisturi": "تمريرات حاسمة",
        "Cartonașe galbene": "بطاقات صفراء", "Cartonașe roșii": "بطاقات حمراء", "Omul meciului": "أفضل لاعب في المباراة",
        "Pe fiecare ligă": "حسب الدوري", "Trofee câștigate": "الكؤوس التي فزت بها", "Ligă": "الدوري", "Echipă": "الفريق",
        "Jucător": "اللاعب", "Etapa": "الجولة", "Competiție": "المسابقة", "Data": "التاريخ", "Meci": "المباراة",
        "Intră în ligă": "انضم إلى دوري", "Creează o ligă": "أنشئ دوريًا", "Clasament": "الترتيب", "Statistici": "الإحصائيات",
        "Echipe și jucători": "الفرق واللاعبون", "Meciuri și program": "المباريات والجدول", "Arbitraj": "التحكيم", "Cupa": "الكأس",
        "Supercupa": "كأس السوبر", "Premii sezon": "جوائز الموسم", "Transferuri": "الانتقالات", "Membri": "الأعضاء",
        "Import / export": "استيراد / تصدير", "Setări ligă": "إعدادات الدوري", "Bine ai venit în Managerul Ligii de Fotbal": "مرحبًا بك في مدير دوري كرة القدم",
        "Numele ligii": "اسم الدوري", "Creează liga": "إنشاء الدوري", "Tipul competiției": "نوع المسابقة",
    },
    "ur": {
        "Limba": "زبان", "Profilul meu": "میری پروفائل", "Jucătorul meu": "میرا کھلاڑی", "Deconectare": "لاگ آؤٹ",
        "Schimbă liga": "لیگ تبدیل کریں", "Navigare": "نیویگیشن", "Autentificare": "لاگ اِن", "Cont nou": "نیا اکاؤنٹ",
        "Nume de utilizator sau e-mail": "صارف نام یا ای میل", "Parolă": "پاس ورڈ", "Intră în cont": "لاگ اِن کریں",
        "Statisticile mele": "میرے اعدادوشمار", "Meciuri jucate": "کھیلے گئے میچ", "Urmează": "آنے والے", "Live": "براہِ راست",
        "Trofee": "ٹرافیاں", "Echipele mele": "میری ٹیمیں", "Goluri": "گول", "Assisturi": "اسسٹ",
        "Cartonașe galbene": "پیلا کارڈ", "Cartonașe roșii": "لال کارڈ", "Omul meciului": "میچ کا بہترین کھلاڑی",
        "Pe fiecare ligă": "ہر لیگ کے مطابق", "Trofee câștigate": "جیتی ہوئی ٹرافیاں", "Ligă": "لیگ", "Echipă": "ٹیم",
        "Jucător": "کھلاڑی", "Etapa": "راؤنڈ", "Competiție": "مقابلہ", "Data": "تاریخ", "Meci": "میچ",
        "Intră în ligă": "لیگ میں شامل ہوں", "Creează o ligă": "لیگ بنائیں", "Clasament": "درجہ بندی", "Statistici": "اعدادوشمار",
        "Echipe și jucători": "ٹیمیں اور کھلاڑی", "Meciuri și program": "میچ اور شیڈول", "Arbitraj": "ریفری", "Cupa": "کپ",
        "Supercupa": "سپر کپ", "Premii sezon": "سیزن ایوارڈز", "Transferuri": "ٹرانسفر", "Membri": "ممبران",
        "Import / export": "درآمد / برآمد", "Setări ligă": "لیگ کی ترتیبات", "Bine ai venit în Managerul Ligii de Fotbal": "فٹبال لیگ مینیجر میں خوش آمدید",
        "Numele ligii": "لیگ کا نام", "Creează liga": "لیگ بنائیں", "Tipul competiției": "مقابلے کی قسم",
    },
    "pcm": {
        "Limba": "Language", "Profilul meu": "My profile", "Jucătorul meu": "My player", "Deconectare": "Log out",
        "Schimbă liga": "Change league", "Navigare": "Navigation", "Autentificare": "Sign in", "Cont nou": "New account",
        "Nume de utilizator sau e-mail": "Username or email", "Parolă": "Password", "Intră în cont": "Sign in",
        "Statisticile mele": "My statistics", "Meciuri jucate": "Matches wey I play", "Urmează": "Next matches", "Live": "Live",
        "Trofee": "Trophies", "Echipele mele": "My teams", "Goluri": "Goals", "Assisturi": "Assists",
        "Cartonașe galbene": "Yellow cards", "Cartonașe roșii": "Red cards", "Omul meciului": "Best player for match",
        "Pe fiecare ligă": "For each league", "Trofee câștigate": "Trophies wey I win", "Ligă": "League", "Echipă": "Team",
        "Jucător": "Player", "Etapa": "Round", "Competiție": "Competition", "Data": "Date", "Meci": "Match",
        "Intră în ligă": "Join league", "Creează o ligă": "Create league", "Clasament": "Table", "Statistici": "Statistics",
        "Echipe și jucători": "Teams and players", "Meciuri și program": "Matches and fixtures", "Arbitraj": "Referee", "Cupa": "Cup",
        "Supercupa": "Super Cup", "Premii sezon": "Season awards", "Transferuri": "Transfers", "Membri": "Members",
        "Import / export": "Import / export", "Setări ligă": "League settings", "Bine ai venit în Managerul Ligii de Fotbal": "You are welcome to Football League Manager",
        "Numele ligii": "League name", "Creează liga": "Create league", "Tipul competiției": "Competition type",
    },
    "arz": {
        "Limba": "اللغة", "Profilul meu": "ملفي الشخصي", "Jucătorul meu": "اللعيب بتاعي", "Deconectare": "تسجيل الخروج",
        "Schimbă liga": "غيّر الدوري", "Navigare": "التنقل", "Autentificare": "تسجيل الدخول", "Cont nou": "حساب جديد",
        "Nume de utilizator sau e-mail": "اسم المستخدم أو الإيميل", "Parolă": "كلمة السر", "Intră în cont": "ادخل للحساب",
        "Statisticile mele": "إحصائياتي", "Meciuri jucate": "الماتشات اللي لعبتها", "Urmează": "الماتشات الجاية", "Live": "مباشر",
        "Trofee": "بطولات", "Echipele mele": "فرقي", "Goluri": "أهداف", "Assisturi": "أسيستات",
        "Cartonașe galbene": "كروت صفرا", "Cartonașe roșii": "كروت حمرا", "Omul meciului": "أحسن لاعب في الماتش",
        "Pe fiecare ligă": "لكل دوري", "Trofee câștigate": "البطولات اللي كسبتها", "Ligă": "دوري", "Echipă": "فريق",
        "Jucător": "لاعب", "Etapa": "جولة", "Competiție": "بطولة", "Data": "التاريخ", "Meci": "ماتش",
        "Intră în ligă": "ادخل دوري", "Creează o ligă": "اعمل دوري", "Clasament": "الترتيب", "Statistici": "الإحصائيات",
        "Echipe și jucători": "الفرق واللاعبين", "Meciuri și program": "الماتشات والجدول", "Arbitraj": "تحكيم", "Cupa": "كأس",
        "Supercupa": "كأس السوبر", "Premii sezon": "جوائز الموسم", "Transferuri": "انتقالات", "Membri": "الأعضاء",
        "Import / export": "استيراد / تصدير", "Setări ligă": "إعدادات الدوري", "Bine ai venit în Managerul Ligii de Fotbal": "أهلاً بيك في مدير دوري الكورة",
        "Numele ligii": "اسم الدوري", "Creează liga": "اعمل الدوري", "Tipul competiției": "نوع البطولة",
    },
})
_EXTRA_TRANSLATIONS = {
    "### Voturile pentru premiile individuale": ("### Individual award voting", "### Votes pour les prix individuels", "### Votaciones de premios individuales"),
    "### Înregistrează returul": ("### Record the second leg", "### Enregistrer le match retour", "### Registrar el partido de vuelta"),
    "### Înregistrează turul": ("### Record the first leg", "### Enregistrer le match aller", "### Registrar el partido de ida"),
    "### Înregistrează un rezultat": ("### Record a result", "### Enregistrer un résultat", "### Registrar un resultado"),
    "#### Acces acordat": ("#### Access granted", "#### Accès accordé", "#### Acceso concedido"),
    "#### Alege-ți echipa și jucătorul": ("#### Choose your team and player", "#### Choisissez votre équipe et votre joueur", "#### Elige tu equipo y jugador"),
    "#### Coduri de acces pentru această ligă": ("#### Access codes for this league", "#### Codes d’accès pour cette ligue", "#### Códigos de acceso de esta liga"),
    "#### Creează Supercupa": ("#### Create the Super Cup", "#### Créer la Supercoupe", "#### Crear la Supercopa"),
    "#### Evenimente live": ("#### Live events", "#### Événements en direct", "#### Eventos en directo"),
    "#### Evenimentele meciului": ("#### Match events", "#### Événements du match", "#### Eventos del partido"),
    "#### Intră cu un cod de ligă": ("#### Join with a league code", "#### Rejoindre avec un code de ligue", "#### Entrar con un código de liga"),
    "#### Istoric meci și vot pentru omul meciului": ("#### Match history and player-of-the-match vote", "#### Historique du match et vote du joueur du match", "#### Historial del partido y votación al mejor jugador"),
    "#### Istoric transferuri": ("#### Transfer history", "#### Historique des transferts", "#### Historial de traspasos"),
    "#### Parolă": ("#### Password", "#### Mot de passe", "#### Contraseña"),
    "#### Statisticile mele": ("#### My statistics", "#### Mes statistiques", "#### Mis estadísticas"),
    "#### Înregistrează un eveniment": ("#### Record an event", "#### Enregistrer un événement", "#### Registrar un evento"),
    "##### ⭐ Votează omul meciului": ("##### ⭐ Vote for player of the match", "##### ⭐ Votez pour le joueur du match", "##### ⭐ Vota al mejor jugador del partido"),
    "**Contribuțiile jucătorilor**": ("**Player contributions**", "**Contributions des joueurs**", "**Aportaciones de los jugadores**"),
    "**Evenimente adăugate**": ("**Added events**", "**Événements ajoutés**", "**Eventos añadidos**"),
    "**Formatul cupelor eliminatorii**": ("**Knockout cup format**", "**Format des coupes à élimination directe**", "**Formato de las copas eliminatorias**"),
    "**Premii de final de sezon**": ("**End-of-season awards**", "**Prix de fin de saison**", "**Premios de final de temporada**"),
    "**Schimbări în meciuri**": ("**Match substitutions**", "**Remplacements pendant les matchs**", "**Cambios en los partidos**"),
    "**Votul pentru omul meciului**": ("**Player-of-the-match voting**", "**Vote du joueur du match**", "**Votación al mejor jugador del partido**"),
    "**⭐ Omul meciului**": ("**⭐ Player of the match**", "**⭐ Joueur du match**", "**⭐ Mejor jugador del partido**"),
    "<div class=\"league-subtitle\">Clasamente, meciuri și cupe într-un singur loc</div>": ("<div class=\"league-subtitle\">Standings, matches and cups in one place</div>", "<div class=\"league-subtitle\">Classements, matchs et coupes au même endroit</div>", "<div class=\"league-subtitle\">Clasificaciones, partidos y copas en un solo lugar</div>"),
    "Acces de vizualizare · nu poți modifica această ligă.": ("View-only access · you cannot edit this league.", "Accès en lecture seule · vous ne pouvez pas modifier cette ligue.", "Acceso de solo lectura · no puedes modificar esta liga."),
    "Acces revocat.": ("Access revoked.", "Accès révoqué.", "Acceso revocado."),
    "Această invitație nu mai este valabilă sau a fost revocată.": ("This invitation has expired or was revoked.", "Cette invitation a expiré ou a été révoquée.", "Esta invitación ha caducado o fue revocada."),
    "Această Supercupă nu are încă o finală configurată.": ("This Super Cup does not have a final set up yet.", "Aucune finale n’est encore configurée pour cette Supercoupe.", "Esta Supercopa aún no tiene una final configurada."),
    "Actualizează poziția": ("Update position", "Mettre à jour le poste", "Actualizar posición"),
    "Acum apari în ligă ca spectator.": ("You now appear in the league as a spectator.", "Vous apparaissez maintenant dans la ligue en tant que spectateur.", "Ahora apareces en la liga como espectador."),
    "Adaugă": ("Add", "Ajouter", "Añadir"), "Adaugă acum": ("Add now", "Ajouter maintenant", "Añadir ahora"),
    "Adaugă cel puțin doi jucători în lotul echipei pentru a înregistra o schimbare.": ("Add at least two players to the team roster to record a substitution.", "Ajoutez au moins deux joueurs à l’effectif pour enregistrer un remplacement.", "Añade al menos dos jugadores a la plantilla para registrar un cambio."),
    "Adaugă cel puțin două echipe pentru a face transferuri.": ("Add at least two teams to make transfers.", "Ajoutez au moins deux équipes pour effectuer des transferts.", "Añade al menos dos equipos para realizar traspasos."),
    "Adaugă cel puțin două echipe pentru a genera programul.": ("Add at least two teams to generate the schedule.", "Ajoutez au moins deux équipes pour générer le calendrier.", "Añade al menos dos equipos para generar el calendario."),
    "Adaugă cel puțin două echipe în ligă înainte să creezi Supercupa.": ("Add at least two teams to the league before creating the Super Cup.", "Ajoutez au moins deux équipes à la ligue avant de créer la Supercoupe.", "Añade al menos dos equipos a la liga antes de crear la Supercopa."),
    "Adaugă cel puțin două echipe.": ("Add at least two teams.", "Ajoutez au moins deux équipes.", "Añade al menos dos equipos."),
    "Adaugă echipe pentru a vedea clasamentul.": ("Add teams to see the standings.", "Ajoutez des équipes pour voir le classement.", "Añade equipos para ver la clasificación."),
    "Adaugă echipe în ligă pentru a-ți asocia un jucător.": ("Add teams to the league so you can link yourself to a player.", "Ajoutez des équipes à la ligue pour pouvoir associer votre profil à un joueur.", "Añade equipos a la liga para vincularte a un jugador."),
    "Adaugă echipă": ("Add team", "Ajouter une équipe", "Añadir equipo"),
    "Adaugă goluri, cartonașe și schimbări. Scorul se actualizează automat; schimbările nu modifică statisticile de goluri.": ("Add goals, cards and substitutions. The score updates automatically; substitutions do not change goal statistics.", "Ajoutez des buts, des cartons et des remplacements. Le score se met à jour automatiquement ; les remplacements ne modifient pas les statistiques de buts.", "Añade goles, tarjetas y cambios. El marcador se actualiza automáticamente; los cambios no modifican las estadísticas de goles."),
    "Adaugă jucători în loturi pentru a putea vota.": ("Add players to the rosters before voting.", "Ajoutez des joueurs aux effectifs avant de voter.", "Añade jugadores a las plantillas para poder votar."),
    "Adaugă mai întâi meciurile în Program, din «Meciuri și program».": ("Add the matches to the schedule first, under “Matches and schedule”.", "Ajoutez d’abord les matchs au calendrier, dans « Matchs et calendrier ».", "Añade primero los partidos al calendario, en «Partidos y calendario»."),
    "Adaugă manual un meci în program": ("Manually add a match to the schedule", "Ajouter manuellement un match au calendrier", "Añadir manualmente un partido al calendario"),
    "Adaugă în lot": ("Add to roster", "Ajouter à l’effectif", "Añadir a la plantilla"),
    "Adaugă în program": ("Add to schedule", "Ajouter au calendrier", "Añadir al calendario"),
    "Adresa aceasta este deja folosită de alt cont.": ("This email address is already used by another account.", "Cette adresse e-mail est déjà utilisée par un autre compte.", "Esta dirección de correo ya está en uso por otra cuenta."),
    "Ai acces doar pentru vizualizare în această ligă.": ("You have view-only access to this league.", "Vous avez un accès en lecture seule à cette ligue.", "Solo tienes acceso de lectura a esta liga."),
    "Ai intrat ca spectator. Poți alege «Jucător» oricând.": ("You joined as a spectator. You can choose “Player” at any time.", "Vous avez rejoint la ligue comme spectateur. Vous pouvez choisir « Joueur » à tout moment.", "Has entrado como espectador. Puedes elegir «Jugador» en cualquier momento."),
    "Ai nevoie de cel puțin două echipe în ligă.": ("You need at least two teams in the league.", "Il faut au moins deux équipes dans la ligue.", "Necesitas al menos dos equipos en la liga."),
    "Alege cel puțin două echipe.": ("Choose at least two teams.", "Choisissez au moins deux équipes.", "Elige al menos dos equipos."),
    "Alege cinci jucători diferiți.": ("Choose five different players.", "Choisissez cinq joueurs différents.", "Elige cinco jugadores distintos."),
    "Alege cinci jucători în ordinea preferinței: locul 1 primește 5 puncte, apoi 4, 3, 2 și 1.": ("Rank five players: 1st place gets 5 points, then 4, 3, 2 and 1.", "Classez cinq joueurs : le 1er reçoit 5 points, puis 4, 3, 2 et 1.", "Ordena cinco jugadores: el 1.º recibe 5 puntos, luego 4, 3, 2 y 1."),
    "Alege cupa": ("Choose cup", "Choisir la coupe", "Elegir copa"), "Alege cupa de administrat": ("Choose a cup to manage", "Choisir une coupe à gérer", "Elige una copa para administrar"),
    "Alege doi jucători diferiți pentru schimbare.": ("Choose two different players for the substitution.", "Choisissez deux joueurs différents pour le remplacement.", "Elige dos jugadores distintos para el cambio."),
    "Alege două echipe diferite pentru a introduce evenimentele.": ("Choose two different teams to enter match events.", "Choisissez deux équipes différentes pour saisir les événements.", "Elige dos equipos distintos para registrar los eventos."),
    "Alege două echipe diferite.": ("Choose two different teams.", "Choisissez deux équipes différentes.", "Elige dos equipos distintos."),
    "Alege jucătorii care ies și intră.": ("Choose the players coming off and going on.", "Choisissez les joueurs qui sortent et qui entrent.", "Elige los jugadores que salen y entran."),
    "Alege jucătorul care intră.": ("Choose the player coming on.", "Choisissez le joueur qui entre.", "Elige el jugador que entra."),
    "Alege liga preferată ca să apară prima sau elimină o ligă din lista acestui cont. Datele ligii rămân salvate.": ("Set a favorite league to show it first, or hide a league from this account. League data stays saved.", "Définissez une ligue favorite pour l’afficher en premier, ou masquez une ligue pour ce compte. Ses données restent enregistrées.", "Marca una liga favorita para mostrarla primero u oculta una liga de esta cuenta. Sus datos se conservan."),
    "Alege meciul": ("Choose match", "Choisir le match", "Elegir partido"), "Alege meciul de arbitrat": ("Choose a match to referee", "Choisir un match à arbitrer", "Elige un partido para arbitrar"),
    "Alege o cupă, urmărește rundele și înregistrează fiecare tur sau retur separat.": ("Choose a cup, follow its rounds, and record each leg separately.", "Choisissez une coupe, suivez ses tours et enregistrez séparément chaque match aller et retour.", "Elige una copa, sigue sus rondas y registra cada partido de ida o vuelta por separado."),
    "Alege sau completează numele jucătorului.": ("Choose or enter the player's name.", "Choisissez ou saisissez le nom du joueur.", "Elige o escribe el nombre del jugador."),
    "Alege sau scrie numele jucătorului.": ("Choose or type the player's name.", "Choisissez ou saisissez le nom du joueur.", "Elige o escribe el nombre del jugador."),
    "Alege un meci": ("Choose a match", "Choisir un match", "Elige un partido"),
    "Alege un top, ca în aplicația principală. Valorile se actualizează după înregistrarea meciurilor.": ("Choose a leaderboard, as in the main app. Values update after matches are recorded.", "Choisissez un classement comme dans l’application principale. Les valeurs sont mises à jour après l’enregistrement des matchs.", "Elige una clasificación como en la aplicación principal. Los valores se actualizan al registrar partidos."),
    "Alege-ți jucătorul": ("Choose your player", "Choisissez votre joueur", "Elige a tu jugador"),
    "Alegerea mea în această ligă": ("My selection in this league", "Mon choix dans cette ligue", "Mi selección en esta liga"),
    "Alegerea ta a fost salvată.": ("Your selection has been saved.", "Votre choix a été enregistré.", "Tu selección se ha guardado."),
    "Anulează acest rezultat și rundele următoare": ("Undo this result and all later rounds", "Annuler ce résultat et les tours suivants", "Anular este resultado y las rondas siguientes"),
    "Anulează meciul selectat": ("Undo the selected match", "Annuler le match sélectionné", "Anular el partido seleccionado"),
    "Anulează rezultatul finalei": ("Undo the final result", "Annuler le résultat de la finale", "Anular el resultado de la final"),
    "Anulează un rezultat": ("Undo a result", "Annuler un résultat", "Anular un resultado"),
    "Arbitraj live": ("Live refereeing", "Arbitrage en direct", "Arbitraje en directo"),
    "Alegerea a fost salvată în ligă, dar nu s-a putut sincroniza cu profilul contului. Statisticile din ligă rămân disponibile.": ("Your selection was saved in the league, but could not be synced to your account profile. League statistics are still available.", "Votre choix a été enregistré dans la ligue, mais n’a pas pu être synchronisé avec votre profil. Les statistiques de la ligue restent disponibles.", "Tu selección se guardó en la liga, pero no se pudo sincronizar con tu perfil. Las estadísticas de la liga siguen disponibles."),
    "Alegerea este salvată în ligă, dar nu s-a sincronizat în profilul contului. Statisticile ligii rămân disponibile.": ("Your selection was saved in the league, but was not synced to your account profile. League statistics remain available.", "Votre choix a été enregistré dans la ligue, mais n’a pas été synchronisé avec votre profil. Les statistiques restent disponibles.", "Tu selección se guardó en la liga, pero no se sincronizó con tu perfil. Las estadísticas siguen disponibles."),
    "Asociază un jucător cu profilul tău pentru a vedea statisticile personale.": ("Link a player to your profile to see your personal statistics.", "Associez un joueur à votre profil pour consulter vos statistiques personnelles.", "Vincula un jugador a tu perfil para ver tus estadísticas personales."),
    "Asocierea a fost salvată în profilul tău.": ("The player selection was saved to your profile.", "Le choix du joueur a été enregistré dans votre profil.", "La selección del jugador se guardó en tu perfil."),
    "Asocierea a fost salvată.": ("The player selection was saved.", "Le choix du joueur a été enregistré.", "La selección del jugador se guardó."),
    "Asocierea jucătorului invitat a fost salvată.": ("The invited player's selection was saved.", "Le choix du joueur invité a été enregistré.", "Se guardó la selección del jugador invitado."),
    "Assist (opțional)": ("Assist (optional)", "Passe décisive (facultatif)", "Asistencia (opcional)"),
    "Baza de date online nu este conectată. Conturile create aici se pot pierde când aplicația repornește. Verifică Secrets în setările Streamlit Cloud.": ("The online database is not connected. Accounts created here may be lost when the app restarts. Check Secrets in Streamlit Cloud settings.", "La base de données en ligne n’est pas connectée. Les comptes créés ici peuvent être perdus au redémarrage. Vérifiez les Secrets dans les paramètres de Streamlit Cloud.", "La base de datos en línea no está conectada. Las cuentas creadas aquí podrían perderse al reiniciar la aplicación. Revisa Secrets en la configuración de Streamlit Cloud."),
    "Cine poate vota?": ("Who can vote?", "Qui peut voter ?", "¿Quién puede votar?"),
    "Cod spectator sau editor": ("Spectator or editor code", "Code spectateur ou éditeur", "Código de espectador o editor"),
    "Codul de acces nu este valid sau a fost schimbat.": ("The access code is invalid or has changed.", "Le code d’accès est invalide ou a été modifié.", "El código de acceso no es válido o ha cambiado."),
    "Codul de editor a fost schimbat sau revocat.": ("The editor code has changed or was revoked.", "Le code éditeur a été modifié ou révoqué.", "El código de editor ha cambiado o fue revocado."),
    "Codul meciului": ("Match code", "Code du match", "Código del partido"),
    "Codul nu este valid pentru această ligă.": ("The code is not valid for this league.", "Ce code n’est pas valide pour cette ligue.", "El código no es válido para esta liga."),
    "Codul trebuie să aibă 12 caractere.": ("The code must be 12 characters long.", "Le code doit comporter 12 caractères.", "El código debe tener 12 caracteres."),
    "Codurile sunt aceleași pentru toți invitații. Le poți copia o singură dată și le poți schimba oricând.": ("The codes are shared by all invitees. Copy them once and change them whenever you like.", "Les codes sont les mêmes pour tous les invités. Copiez-les une fois et modifiez-les à tout moment.", "Los códigos son iguales para todos los invitados. Cópialos una vez y cámbialos cuando quieras."),
    "Codurile sunt vizibile doar proprietarului și editorilor. Trimite codul doar arbitrului ales pentru meci.": ("Only the owner and editors can see the codes. Share a match code only with its referee.", "Seuls le propriétaire et les éditeurs voient les codes. Transmettez le code du match uniquement à l’arbitre choisi.", "Solo el propietario y los editores pueden ver los códigos. Comparte el código del partido solo con el árbitro elegido."),
    "Conectarea se salvează pe acest dispozitiv…": ("Saving your sign-in on this device…", "Enregistrement de votre connexion sur cet appareil…", "Guardando el inicio de sesión en este dispositivo…"),
    "Confirm că folosesc clasamentul actual": ("I confirm that I am using the current standings", "Je confirme utiliser le classement actuel", "Confirmo que uso la clasificación actual"),
    "Confirmă folosirea clasamentului actual pentru a continua.": ("Confirm that you are using the current standings to continue.", "Confirmez que vous utilisez le classement actuel pour continuer.", "Confirma que usas la clasificación actual para continuar."),
    "Confirmă parola nouă": ("Confirm new password", "Confirmer le nouveau mot de passe", "Confirmar la nueva contraseña"),
    "Contul a fost creat.": ("Your account has been created.", "Votre compte a été créé.", "Se ha creado tu cuenta."),
    "Contul a fost creat. Se salvează conectarea pe acest dispozitiv…": ("Your account was created. Saving your sign-in on this device…", "Votre compte a été créé. Enregistrement de votre connexion sur cet appareil…", "Se creó tu cuenta. Guardando el inicio de sesión en este dispositivo…"),
    "Contul nu a putut fi salvat în baza de date. Verifică setările Supabase din Streamlit Cloud.": ("The account could not be saved to the database. Check the Supabase settings in Streamlit Cloud.", "Le compte n’a pas pu être enregistré. Vérifiez les paramètres Supabase dans Streamlit Cloud.", "No se pudo guardar la cuenta en la base de datos. Revisa la configuración de Supabase en Streamlit Cloud."),
    "Corectează statisticile unui jucător": ("Correct a player's statistics", "Corriger les statistiques d’un joueur", "Corregir las estadísticas de un jugador"),
    "Corecțiile rămân salvate și după recalcularea statisticilor din istoricul meciurilor.": ("Corrections remain saved even after statistics are recalculated from match history.", "Les corrections restent enregistrées même après le recalcul des statistiques à partir de l’historique des matchs.", "Las correcciones se conservan aunque se recalculen las estadísticas a partir del historial de partidos."),
    "Creează cont": ("Create account", "Créer un compte", "Crear cuenta"),
    "Creează cupa": ("Create cup", "Créer la coupe", "Crear copa"),
    "Creează finala Supercupei": ("Create the Super Cup final", "Créer la finale de la Supercoupe", "Crear la final de la Supercopa"),
    "Creează o cupă ca să vezi tabloul și să introduci rezultatele.": ("Create a cup to view the bracket and enter results.", "Créez une coupe pour afficher le tableau et saisir les résultats.", "Crea una copa para ver el cuadro y registrar resultados."),
    "Cum se încheie meciul?": ("How does the match end?", "Comment le match se termine-t-il ?", "¿Cómo termina el partido?"),
    "Cum vrei să apari în ligă?": ("How would you like to appear in the league?", "Comment souhaitez-vous apparaître dans la ligue ?", "¿Cómo quieres aparecer en la liga?"),
    "Cupa a fost ștearsă.": ("The cup was deleted.", "La coupe a été supprimée.", "Se eliminó la copa."),
    "Cupă": ("Cup", "Coupe", "Copa"), "Câștigătoare": ("Winner", "Vainqueur", "Ganadora"),
    "Câștigătoare la penaltyuri": ("Winner on penalties", "Vainqueur aux tirs au but", "Ganadora en los penaltis"),
    "Câștigător": ("Winner", "Vainqueur", "Ganador"),
    "Câștigătorul va apărea automat după ce există rezultate.": ("The winner will appear automatically once results are entered.", "Le vainqueur apparaîtra automatiquement une fois les résultats saisis.", "El ganador aparecerá automáticamente cuando haya resultados."),
    "Da": ("Yes", "Oui", "Sí"), "Dacă egalitatea persistă în cupă": ("If the cup tie is still level", "Si l’égalité persiste en coupe", "Si persiste el empate en la copa"),
    "Dacă finala Supercupei se termină egal": ("If the Super Cup final ends in a draw", "Si la finale de la Supercoupe se termine par un nul", "Si la final de la Supercopa termina en empate"),
    "Data nașterii": ("Date of birth", "Date de naissance", "Fecha de nacimiento"), "Denumire": ("Name", "Nom", "Nombre"),
    "Descarcă liga activă": ("Download active league", "Télécharger la ligue active", "Descargar la liga activa"),
    "Deschide meciul": ("Open match", "Ouvrir le match", "Abrir partido"), "Deschide votul pentru premii": ("Open award voting", "Ouvrir le vote des prix", "Abrir la votación de premios"),
    "Doar proprietarul ligii poate administra accesul membrilor.": ("Only the league owner can manage member access.", "Seul le propriétaire de la ligue peut gérer l’accès des membres.", "Solo el propietario de la liga puede administrar el acceso de los miembros."),
    "Durata unei reprize (minute)": ("Half length (minutes)", "Durée d’une mi-temps (minutes)", "Duración de cada parte (minutos)"),
    "Echipa a folosit deja toate cele cinci schimbări permise în acest meci.": ("The team has already used all five substitutions allowed in this match.", "L’équipe a déjà utilisé les cinq remplacements autorisés dans ce match.", "El equipo ya ha utilizado los cinco cambios permitidos en este partido."),
    "Echipa a folosit deja toate cele cinci schimbări permise.": ("The team has already used all five allowed substitutions.", "L’équipe a déjà utilisé les cinq remplacements autorisés.", "El equipo ya ha utilizado los cinco cambios permitidos."),
    "Echipa a folosit deja toate schimbările permise pentru meci.": ("The team has already used all substitutions allowed for the match.", "L’équipe a déjà utilisé tous les remplacements autorisés pour le match.", "El equipo ya ha utilizado todos los cambios permitidos en el partido."),
    "Echipa a fost redenumită.": ("The team was renamed.", "L’équipe a été renommée.", "Se cambió el nombre del equipo."),
    "Echipa aleasă nu are jucători în lot.": ("The selected team has no players in its roster.", "L’équipe sélectionnée n’a aucun joueur dans son effectif.", "El equipo seleccionado no tiene jugadores en la plantilla."),
    "Echipa aleasă nu are încă jucători în lot.": ("The selected team does not have any rostered players yet.", "L’équipe sélectionnée n’a pas encore de joueurs dans son effectif.", "El equipo seleccionado aún no tiene jugadores en la plantilla."),
    "Echipa există deja.": ("The team already exists.", "Cette équipe existe déjà.", "El equipo ya existe."),
    "Echipa nu are jucători în lot încă.": ("The team does not have any rostered players yet.", "L’équipe n’a pas encore de joueurs dans son effectif.", "El equipo aún no tiene jugadores en la plantilla."),
    "Echipa nu are încă jucători în lot.": ("The team does not have any rostered players yet.", "L’équipe n’a pas encore de joueurs dans son effectif.", "El equipo aún no tiene jugadores en la plantilla."),
    "Echipa ta": ("Your team", "Votre équipe", "Tu equipo"), "Echipe participante": ("Participating teams", "Équipes participantes", "Equipos participantes"),
    "Echipe și loturi": ("Teams and rosters", "Équipes et effectifs", "Equipos y plantillas"),
    "Echipele se stabilesc după runda anterioară.": ("Teams are determined after the previous round.", "Les équipes sont déterminées après le tour précédent.", "Los equipos se determinan después de la ronda anterior."),
    "Editează un rezultat": ("Edit a result", "Modifier un résultat", "Editar un resultado"),
    "Egalitate după minutele regulamentare. Se joacă două reprize de prelungiri (minutele 91–120).": ("The match is level after regulation time. Two extra-time periods are played (minutes 91–120).", "Égalité après le temps réglementaire. Deux périodes de prolongation sont jouées (minutes 91 à 120).", "Empate tras el tiempo reglamentario. Se juegan dos periodos de prórroga (minutos 91–120)."),
    "Egalitate în continuare. Alege echipa care se califică după penaltyuri.": ("The tie is still level. Choose the team that advances after penalties.", "L’égalité persiste. Choisissez l’équipe qualifiée après les tirs au but.", "El empate continúa. Elige el equipo que se clasifica tras los penaltis."),
    "Etapa (lasă 0 dacă nu se aplică)": ("Round (enter 0 if not applicable)", "Journée (saisissez 0 si non applicable)", "Jornada (escribe 0 si no corresponde)"),
    "Eveniment": ("Event", "Événement", "Evento"), "Evenimentele vor apărea aici în timp real.": ("Events will appear here in real time.", "Les événements apparaîtront ici en temps réel.", "Los eventos aparecerán aquí en tiempo real."),
    "Evenimentul trebuie să aparțină uneia dintre echipe.": ("The event must belong to one of the teams.", "L’événement doit être associé à l’une des équipes.", "El evento debe pertenecer a uno de los equipos."),
    "Există deja o cupă cu acest nume. Alege-o din lista cupelor, nu o crea din nou.": ("A cup with this name already exists. Choose it from the cup list instead of creating it again.", "Une coupe portant ce nom existe déjà. Choisissez-la dans la liste au lieu de la recréer.", "Ya existe una copa con ese nombre. Elígela de la lista en lugar de crearla otra vez."),
    "Există deja o ligă cu acest nume în cont.": ("A league with this name already exists in your account.", "Une ligue portant ce nom existe déjà dans votre compte.", "Ya existe una liga con ese nombre en tu cuenta."),
    "Finala se joacă între câștigătoarea unei cupe și campioana ligii. Dacă aceeași echipă câștigă ambele trofee, adversara este echipa de pe locul 2.": ("The final is played between a cup winner and the league champion. If the same team wins both, the runner-up is the opponent.", "La finale oppose la gagnante d’une coupe à la championne de la ligue. Si la même équipe remporte les deux titres, la deuxième équipe du classement est son adversaire.", "La final enfrenta a la campeona de copa con la campeona de liga. Si el mismo equipo gana ambos títulos, se enfrenta al segundo clasificado."),
    "Forma ultimelor cinci meciuri: V = victorie · E = egal · Î = înfrângere": ("Last five matches: W = win · D = draw · L = loss", "Cinq derniers matchs : V = victoire · N = nul · D = défaite", "Últimos cinco partidos: G = ganado · E = empate · P = perdido"),
    "Format pentru cupele noi": ("Format for new cups", "Format des nouvelles coupes", "Formato para nuevas copas"),
    "Format pentru Supercupele noi": ("Format for new Super Cups", "Format des nouvelles Supercoupes", "Formato para nuevas Supercopas"),
    "Formatele se aplică competițiilor noi. Pentru o cupă sau Supercupă existentă, formatul se poate schimba înainte de primul rezultat.": ("These formats apply to new competitions. For an existing cup or Super Cup, the format can be changed before the first result.", "Ces formats s’appliquent aux nouvelles compétitions. Le format d’une coupe ou Supercoupe existante peut être modifié avant le premier résultat.", "Estos formatos se aplican a nuevas competiciones. El formato de una copa o Supercopa existente puede cambiarse antes del primer resultado."),
    "Formatul acestei cupe": ("This cup's format", "Format de cette coupe", "Formato de esta copa"),
    "Formatul cupei a fost salvat.": ("The cup format was saved.", "Le format de la coupe a été enregistré.", "Se guardó el formato de la copa."),
    "Formatul finalei": ("Final format", "Format de la finale", "Formato de la final"),
    "Formatul nu poate fi schimbat după înregistrarea primului rezultat.": ("The format cannot be changed after the first result is recorded.", "Le format ne peut pas être modifié après l’enregistrement du premier résultat.", "El formato no se puede cambiar después de registrar el primer resultado."),
    "Gazda și oaspeții trebuie să fie echipe diferite.": ("The home and away teams must be different.", "Les équipes à domicile et à l’extérieur doivent être différentes.", "Los equipos local y visitante deben ser distintos."),
    "Generează cod nou": ("Generate new code", "Générer un nouveau code", "Generar un código nuevo"),
    "Generează programul": ("Generate schedule", "Générer le calendrier", "Generar calendario"),
    "Goluri în această ligă": ("Goals in this league", "Buts dans cette ligue", "Goles en esta liga"),
    "Ieși din invitație": ("Leave invitation", "Quitter l’invitation", "Salir de la invitación"),
    "Import / export JSON": ("JSON import / export", "Import / export JSON", "Importar / exportar JSON"),
    "Importă liga": ("Import league", "Importer la ligue", "Importar liga"),
    "Importă peste liga activă": ("Import over the active league", "Remplacer la ligue active par un import", "Importar sobre la liga activa"),
    "Importă un fișier JSON de ligă": ("Import a league JSON file", "Importer un fichier JSON de ligue", "Importar un archivo JSON de liga"),
    "Introdu codul primit de la proprietarul sau editorul ligii ca să poți arbitra acel meci.": ("Enter the code from the league owner or editor to referee that match.", "Saisissez le code fourni par le propriétaire ou l’éditeur pour arbitrer ce match.", "Introduce el código del propietario o editor de la liga para arbitrar ese partido."),
    "Introdu golurile din minutele regulamentare (1–90).": ("Enter goals scored in regulation time (1–90).", "Saisissez les buts marqués pendant le temps réglementaire (1–90).", "Introduce los goles del tiempo reglamentario (1–90)."),
    "Introdu numele echipei.": ("Enter the team name.", "Saisissez le nom de l’équipe.", "Introduce el nombre del equipo."),
    "Introdu o adresă de e-mail validă.": ("Enter a valid email address.", "Saisissez une adresse e-mail valide.", "Introduce una dirección de correo válida."),
    "Introduc evenimentele": ("Enter events", "Saisir les événements", "Registrar eventos"),
    "Intră la pauză": ("Start halftime", "Passer à la mi-temps", "Iniciar el descanso"),
    "Intră în cont sau accesează liga prin invitație pentru a vota.": ("Sign in or join the league through an invitation to vote.", "Connectez-vous ou rejoignez la ligue avec une invitation pour voter.", "Inicia sesión o accede a la liga con una invitación para votar."),
    "Invitația nu mai permite modificarea ligii.": ("This invitation no longer allows league edits.", "Cette invitation ne permet plus de modifier la ligue.", "Esta invitación ya no permite modificar la liga."),
    "Invitații introduc codul pe ecranul de autentificare. Schimbarea unui cod dezactivează imediat codul vechi.": ("Invitees enter the code on the sign-in screen. Changing a code immediately disables the old one.", "Les invités saisissent le code sur l’écran de connexion. Tout changement désactive immédiatement l’ancien code.", "Los invitados introducen el código en la pantalla de inicio de sesión. Al cambiarlo, el código anterior se desactiva inmediatamente."),
    "Jucător care iese": ("Player coming off", "Joueur remplacé", "Jugador que sale"),
    "Jucător care intră": ("Player coming on", "Joueur entrant", "Jugador que entra"),
    "Jucător din lot": ("Roster player", "Joueur de l’effectif", "Jugador de la plantilla"),
    "Jucător nou": ("New player", "Nouveau joueur", "Jugador nuevo"),
    "Jucătorii pot vota, dar nu își pot alege propriul profil.": ("Players can vote, but cannot vote for their own profile.", "Les joueurs peuvent voter, mais pas pour leur propre profil.", "Los jugadores pueden votar, pero no por su propio perfil."),
    "Jucătorul a ieșit deja și nu mai poate fi schimbat din nou în acest meci.": ("This player has already been substituted off and cannot be substituted again in this match.", "Ce joueur a déjà été remplacé et ne peut plus être remplacé à nouveau pendant ce match.", "Este jugador ya ha sido sustituido y no puede volver a cambiarse en este partido."),
    "Jucătorul care a ieșit mai devreme nu mai poate reintra.": ("A player who has already come off cannot return.", "Un joueur déjà remplacé ne peut pas revenir sur le terrain.", "Un jugador que ya salió no puede volver a entrar."),
    "Jucătorul există deja în lot.": ("The player is already in the roster.", "Ce joueur figure déjà dans l’effectif.", "El jugador ya está en la plantilla."),
    "Liga a fost importată.": ("The league was imported.", "La ligue a été importée.", "Se importó la liga."),
    "Liga mea": ("My league", "Ma ligue", "Mi liga"),
    "Liga nu a putut fi creată și confirmată în stocare.": ("The league could not be created and confirmed in storage.", "La ligue n’a pas pu être créée et confirmée dans le stockage.", "No se pudo crear y confirmar la liga en el almacenamiento."),
    "Liga nu are încă echipe.": ("The league does not have any teams yet.", "La ligue ne compte pas encore d’équipes.", "La liga aún no tiene equipos."),
    "Liga nu are încă echipe. Deocamdată poți rămâne spectator.": ("The league does not have any teams yet. You can remain a spectator for now.", "La ligue ne compte pas encore d’équipes. Vous pouvez rester spectateur pour le moment.", "La liga aún no tiene equipos. Por ahora puedes seguir como espectador."),
    "Liga selectată nu are echipe încă.": ("The selected league does not have any teams yet.", "La ligue sélectionnée ne compte pas encore d’équipes.", "La liga seleccionada aún no tiene equipos."),
    "Ligă + cupă": ("League + cup", "Ligue + coupe", "Liga + copa"),
    "Limita de cinci schimbări se aplică separat fiecărei echipe și include prelungirile.": ("The five-substitution limit applies separately to each team and includes extra time.", "La limite de cinq remplacements s’applique séparément à chaque équipe, prolongations comprises.", "El límite de cinco cambios se aplica por separado a cada equipo e incluye la prórroga."),
    "Marcatorul nu poate să-și dea assist lui însuși.": ("A scorer cannot assist their own goal.", "Le buteur ne peut pas être passeur décisif sur son propre but.", "El goleador no puede asistirse a sí mismo."),
    "Marchează pauza": ("Mark halftime", "Marquer la mi-temps", "Marcar el descanso"),
    "Meci de editat": ("Match to edit", "Match à modifier", "Partido que editar"),
    "Meci de jucat": ("Match to play", "Match à jouer", "Partido por jugar"),
    "Meci programat (opțional)": ("Scheduled match (optional)", "Match programmé (facultatif)", "Partido programado (opcional)"),
    "Meci salvat.": ("Match saved.", "Match enregistré.", "Partido guardado."),
    "Meciul a fost adăugat în program.": ("The match was added to the schedule.", "Le match a été ajouté au calendrier.", "El partido se añadió al calendario."),
    "Meciul a fost salvat fără evenimente individuale.": ("The match was saved without individual events.", "Le match a été enregistré sans événements individuels.", "El partido se guardó sin eventos individuales."),
    "Meciul nu mai există în program.": ("The match is no longer in the schedule.", "Le match ne figure plus au calendrier.", "El partido ya no está en el calendario."),
    "Meciuri live": ("Live matches", "Matchs en direct", "Partidos en directo"),
    "Membri și acces la ligă": ("Members and league access", "Membres et accès à la ligue", "Miembros y acceso a la liga"),
    "Merge la": ("Goes to", "Va à", "Va a"),
    "Metoda de acordare a premiilor a fost salvată.": ("The award method was saved.", "La méthode d’attribution des prix a été enregistrée.", "Se guardó el método de concesión de premios."),
    "Metoda de acordare a premiilor individuale": ("Individual award method", "Méthode d’attribution des prix individuels", "Método de concesión de premios individuales"),
    "Minut": ("Minute", "Minute", "Minuto"),
    "Minute de prelungire pentru prima repriză": ("Added minutes for the first half", "Minutes de temps additionnel pour la première mi-temps", "Minutos añadidos en la primera parte"),
    "Minute de prelungire pentru repriza a doua": ("Added minutes for the second half", "Minutes de temps additionnel pour la deuxième mi-temps", "Minutos añadidos en la segunda parte"),
    "Motivul (opțional)": ("Reason (optional)", "Motif (facultatif)", "Motivo (opcional)"),
    "Nespecificată": ("Not specified", "Non précisé", "Sin especificar"), "Nu": ("No", "Non", "No"),
    "Nu ai adăugat încă evenimente. Poți salva scorul 0–0.": ("You have not added any events yet. You can save the 0–0 score.", "Vous n’avez encore ajouté aucun événement. Vous pouvez enregistrer le score de 0–0.", "Aún no has añadido eventos. Puedes guardar el marcador 0–0."),
    "Nu ai fost încă în nicio ligă. Când intri într-o ligă, ea va apărea aici.": ("You have not joined any leagues yet. Leagues you join will appear here.", "Vous n’avez encore rejoint aucune ligue. Les ligues que vous rejoindrez apparaîtront ici.", "Aún no has estado en ninguna liga. Las ligas a las que te unas aparecerán aquí."),
    "Nu ai ligi în acest cont.": ("There are no leagues in this account.", "Ce compte ne contient aucune ligue.", "Esta cuenta no tiene ligas."),
    "Nu ai partajat această ligă cu niciun cont încă.": ("You have not shared this league with any accounts yet.", "Vous n’avez pas encore partagé cette ligue avec un compte.", "Aún no has compartido esta liga con ninguna cuenta."),
    "Nu ai trofee câștigate în ligile asociate încă.": ("You have not won any trophies in your linked leagues yet.", "Vous n’avez encore remporté aucun trophée dans les ligues associées à votre profil.", "Aún no has ganado trofeos en las ligas vinculadas."),
    "Nu ai încă ligi. Creează una sau importă un fișier JSON.": ("You do not have any leagues yet. Create one or import a JSON file.", "Vous n’avez pas encore de ligue. Créez-en une ou importez un fichier JSON.", "Aún no tienes ligas. Crea una o importa un archivo JSON."),
    "Nu am putut salva intrarea ca jucător. Verifică dacă aplicația Streamlit Cloud este actualizată și încearcă din nou.": ("We could not save your player access. Make sure the Streamlit Cloud app is up to date and try again.", "Impossible d’enregistrer votre accès en tant que joueur. Vérifiez que l’application Streamlit Cloud est à jour, puis réessayez.", "No se pudo guardar tu acceso como jugador. Comprueba que la aplicación de Streamlit Cloud esté actualizada e inténtalo de nuevo."),
    "Nu există alți jucători eligibili pentru vot.": ("There are no other eligible players to vote for.", "Aucun autre joueur n’est éligible au vote.", "No hay otros jugadores que puedan recibir votos."),
    "Nu există date de afișat încă.": ("There is no data to display yet.", "Il n’y a pas encore de données à afficher.", "Aún no hay datos que mostrar."),
    "Nu există meciuri live în acest moment.": ("There are no live matches right now.", "Il n’y a aucun match en direct pour le moment.", "No hay partidos en directo ahora mismo."),
    "Nu există meciuri rămase în program.": ("There are no matches left on the schedule.", "Il ne reste aucun match au calendrier.", "No quedan partidos en el calendario."),
    "Nu există un alt jucător eligibil care să intre.": ("There is no other eligible player to come on.", "Aucun autre joueur ne peut entrer.", "No hay otro jugador que pueda entrar."),
    "Nu există încă meciuri înregistrate în această ligă.": ("No matches have been recorded in this league yet.", "Aucun match n’a encore été enregistré dans cette ligue.", "Aún no hay partidos registrados en esta liga."),
    "Nu există încă un meci disponibil. Completează meciurile rundei curente ca să se stabilească următorii adversari.": ("No match is available yet. Complete the current round to determine the next opponents.", "Aucun match n’est encore disponible. Terminez le tour en cours pour déterminer les prochains adversaires.", "Aún no hay partidos disponibles. Completa la ronda actual para determinar los próximos enfrentamientos."),
    "Nu mai sunt jucători eligibili pentru a ieși; cei schimbați nu pot reintra.": ("No eligible players can come off; substituted players cannot return.", "Aucun joueur éligible ne peut sortir ; les joueurs remplacés ne peuvent pas revenir.", "No quedan jugadores que puedan salir; los sustituidos no pueden volver a entrar."),
    "Nu pot accesa baza de date a conturilor. Verifică setările Supabase din Streamlit Cloud și încearcă din nou.": ("I cannot access the account database. Check the Supabase settings in Streamlit Cloud and try again.", "Impossible d’accéder à la base de données des comptes. Vérifiez les paramètres Supabase dans Streamlit Cloud, puis réessayez.", "No se puede acceder a la base de datos de cuentas. Revisa la configuración de Supabase en Streamlit Cloud e inténtalo de nuevo."),
    "Nu se votează omul meciului pentru o victorie la masa verde.": ("Player of the match is not voted on for a forfeit win.", "Il n’y a pas de vote du joueur du match en cas de victoire par forfait.", "No se vota al mejor jugador en una victoria por incomparecencia."),
    "Nume în lotul nou (opțional)": ("Name in the new roster (optional)", "Nom dans le nouvel effectif (facultatif)", "Nombre en la nueva plantilla (opcional)"),
    "Numele celui care a dat assist": ("Name of the player who provided the assist", "Nom du joueur ayant fait la passe décisive", "Nombre del jugador que dio la asistencia"),
    "Numele celui cu assist": ("Assisting player's name", "Nom du passeur décisif", "Nombre del jugador que asistió"),
    "Numele cupei": ("Cup name", "Nom de la coupe", "Nombre de la copa"), "Numele jucătorului": ("Player name", "Nom du joueur", "Nombre del jugador"),
    "Parola a fost schimbată.": ("The password was changed.", "Le mot de passe a été modifié.", "Se cambió la contraseña."),
    "Parola curentă": ("Current password", "Mot de passe actuel", "Contraseña actual"),
    "Parola curentă este greșită.": ("The current password is incorrect.", "Le mot de passe actuel est incorrect.", "La contraseña actual es incorrecta."),
    "Parola nouă": ("New password", "Nouveau mot de passe", "Nueva contraseña"),
    "Parola nouă trebuie să aibă cel puțin 6 caractere.": ("The new password must be at least 6 characters long.", "Le nouveau mot de passe doit comporter au moins 6 caractères.", "La nueva contraseña debe tener al menos 6 caracteres."),
    "Parolele noi nu coincid.": ("The new passwords do not match.", "Les nouveaux mots de passe ne correspondent pas.", "Las nuevas contraseñas no coinciden."),
    "Parolele nu coincid.": ("The passwords do not match.", "Les mots de passe ne correspondent pas.", "Las contraseñas no coinciden."),
    "Pleacă de la": ("Start from", "Partir de", "Partir de"), "Pornește de la": ("Start from", "Partir de", "Partir de"),
    "Pornește prima repriză": ("Start the first half", "Lancer la première mi-temps", "Iniciar la primera parte"),
    "Poziția a fost actualizată.": ("The position was updated.", "Le poste a été mis à jour.", "Se actualizó la posición."),
    "Poziție": ("Position", "Poste", "Posición"), "Poziție nouă": ("New position", "Nouveau poste", "Nueva posición"),
    "Prea multe încercări. Așteaptă un minut și încearcă din nou.": ("Too many attempts. Wait one minute and try again.", "Trop de tentatives. Attendez une minute avant de réessayer.", "Demasiados intentos. Espera un minuto e inténtalo de nuevo."),
    "Premii de sezon": ("Season awards", "Prix de la saison", "Premios de temporada"),
    "Premiile pentru echipe se aleg direct de proprietar/editor; acest premiu se decide prin vot.": ("Team awards are chosen directly by the owner/editor; this award is decided by vote.", "Les prix d’équipe sont attribués directement par le propriétaire ou l’éditeur ; ce prix est décidé par vote.", "El propietario o editor elige directamente los premios de equipo; este premio se decide por votación."),
    "Premiul a fost salvat.": ("The award was saved.", "Le prix a été enregistré.", "Se guardó el premio."),
    "Profil personal": ("Personal profile", "Profil personnel", "Perfil personal"),
    "Profilul a fost asociat jucătorului.": ("Your profile was linked to the player.", "Votre profil a été associé au joueur.", "Tu perfil se vinculó al jugador."),
    "Profilul a fost salvat.": ("The profile was saved.", "Le profil a été enregistré.", "Se guardó el perfil."),
    "Profilul a fost salvat. Te poți conecta și cu e-mailul.": ("The profile was saved. You can also sign in with your email.", "Le profil a été enregistré. Vous pouvez aussi vous connecter avec votre adresse e-mail.", "Se guardó el perfil. También puedes iniciar sesión con tu correo."),
    "Program": ("Schedule", "Calendrier", "Calendario"),
    "Proprietarul sau editorul alege câștigătorii direct. Clasamentul și statisticile sunt sugestii, nu acordă premii automat.": ("The owner or editor chooses winners directly. Standings and statistics are suggestions and do not award prizes automatically.", "Le propriétaire ou l’éditeur choisit directement les gagnants. Le classement et les statistiques sont indicatifs et n’attribuent pas automatiquement de prix.", "El propietario o editor elige directamente a los ganadores. La clasificación y las estadísticas son orientativas y no otorgan premios automáticamente."),
    "Redenumește echipa": ("Rename team", "Renommer l’équipe", "Cambiar nombre del equipo"),
    "Regula de departajare se ia din Setări ligă și se aplică după timpul regulamentar sau după scorul agregat al returului.": ("The tie-break rule is taken from League settings and applies after regulation time or the aggregate second-leg score.", "La règle de départage est définie dans les paramètres de la ligue et s’applique après le temps réglementaire ou le score cumulé du match retour.", "La regla de desempate se configura en Ajustes de liga y se aplica tras el tiempo reglamentario o el marcador global de la vuelta."),
    "Regula schimbărilor": ("Substitution rule", "Règle des remplacements", "Regla de cambios"),
    "Regula schimbărilor a fost salvată.": ("The substitution rule was saved.", "La règle des remplacements a été enregistrée.", "Se guardó la regla de cambios."),
    "Returul finalei urmează.": ("The final's second leg is next.", "Le match retour de la finale est à venir.", "La vuelta de la final está pendiente."),
    "Returul nu a fost jucat încă.": ("The second leg has not been played yet.", "Le match retour n’a pas encore été joué.", "La vuelta aún no se ha jugado."),
    "Returul urmează.": ("The second leg is next.", "Le match retour est à venir.", "La vuelta está pendiente."),
    "Rezultate": ("Results", "Résultats", "Resultados"), "Rezultatul a fost corectat.": ("The result was corrected.", "Le résultat a été corrigé.", "Se corrigió el resultado."),
    "Reîncearcă intrarea": ("Retry joining", "Réessayer de rejoindre", "Volver a intentar entrar"),
    "Reîncearcă salvarea conectării": ("Retry saving sign-in", "Réessayer d’enregistrer la connexion", "Volver a guardar el inicio de sesión"),
    "Rol actualizat.": ("Role updated.", "Rôle mis à jour.", "Rol actualizado."),
    "Salvează ca spectator": ("Save as spectator", "Enregistrer comme spectateur", "Guardar como espectador"),
    "Salvează denumirea": ("Save name", "Enregistrer le nom", "Guardar nombre"),
    "Salvează formatul cupei": ("Save cup format", "Enregistrer le format de la coupe", "Guardar formato de copa"),
    "Salvează formatul Supercupei": ("Save Super Cup format", "Enregistrer le format de la Supercoupe", "Guardar formato de Supercopa"),
    "Salvează meciul": ("Save match", "Enregistrer le match", "Guardar partido"),
    "Salvează metoda premiilor": ("Save award method", "Enregistrer la méthode d’attribution", "Guardar método de premios"),
    "Salvează modificările": ("Save changes", "Enregistrer les modifications", "Guardar cambios"),
    "Salvează numele": ("Save name", "Enregistrer le nom", "Guardar nombre"),
    "Salvează poziția": ("Save position", "Enregistrer le poste", "Guardar posición"),
    "Salvează regula schimbărilor": ("Save substitution rule", "Enregistrer la règle des remplacements", "Guardar regla de cambios"),
    "Salvează setările cupelor": ("Save cup settings", "Enregistrer les paramètres des coupes", "Guardar ajustes de copas"),
    "Salvează setările votului": ("Save voting settings", "Enregistrer les paramètres du vote", "Guardar ajustes de votación"),
    "Salvează statisticile": ("Save statistics", "Enregistrer les statistiques", "Guardar estadísticas"),
    "Salvează votul": ("Save vote", "Enregistrer le vote", "Guardar voto"),
    "Salvează și pornește prelungirile": ("Save and start extra time", "Enregistrer et lancer les prolongations", "Guardar e iniciar la prórroga"),
    "Scorul, cronometrul și evenimentele se actualizează automat.": ("The score, clock and events update automatically.", "Le score, le chronomètre et les événements se mettent à jour automatiquement.", "El marcador, el cronómetro y los eventos se actualizan automáticamente."),
    "Se salvează conectarea pe acest dispozitiv. Te vei conecta imediat ce browserul confirmă salvarea.": ("Saving your sign-in on this device. You will be signed in as soon as the browser confirms.", "Enregistrement de votre connexion sur cet appareil. Vous serez connecté dès que le navigateur aura confirmé l’enregistrement.", "Guardando el inicio de sesión en este dispositivo. Entrarás cuando el navegador confirme el guardado."),
    "Setarea votului pentru omul meciului a fost salvată.": ("Player-of-the-match voting settings were saved.", "Les paramètres du vote du joueur du match ont été enregistrés.", "Se guardó la configuración de la votación al mejor jugador."),
    "Setări cupă și ștergere": ("Cup settings and deletion", "Paramètres et suppression de la coupe", "Ajustes y eliminación de copa"),
    "Setări Supercupă": ("Super Cup settings", "Paramètres de la Supercoupe", "Ajustes de Supercopa"),
    "Setările cupelor și Supercupei au fost salvate.": ("Cup and Super Cup settings were saved.", "Les paramètres des coupes et de la Supercoupe ont été enregistrés.", "Se guardaron los ajustes de las copas y la Supercopa."),
    "Spectator": ("Spectator", "Spectateur", "Espectador"), "Statistici jucători": ("Player statistics", "Statistiques des joueurs", "Estadísticas de jugadores"),
    "Sunt necesari cel puțin cinci jucători eligibili pentru acest vot.": ("At least five eligible players are required for this vote.", "Au moins cinq joueurs éligibles sont nécessaires pour ce vote.", "Se necesitan al menos cinco jugadores aptos para esta votación."),
    "Supercupa activă": ("Active Super Cup", "Supercoupe active", "Supercopa activa"),
    "Supercupele create vor apărea aici.": ("Created Super Cups will appear here.", "Les Supercoupes créées apparaîtront ici.", "Las Supercopas creadas aparecerán aquí."),
    "Termină o cupă eliminatorie. Câștigătoarea ei va juca Supercupa.": ("Finish a knockout cup. Its winner will play in the Super Cup.", "Terminez une coupe à élimination directe. Sa gagnante disputera la Supercoupe.", "Completa una copa eliminatoria. Su ganadora jugará la Supercopa."),
    "Toate meciurile din program au fost jucate.": ("All scheduled matches have been played.", "Tous les matchs du calendrier ont été joués.", "Se han jugado todos los partidos del calendario."),
    "Toate rundele s-au încheiat. Cupa are câștigătoare.": ("All rounds are complete. The cup has a winner.", "Tous les tours sont terminés. La coupe a une gagnante.", "Han terminado todas las rondas. La copa ya tiene ganadora."),
    "Tragerea la sorți se face automat. Dacă numărul echipelor nu se potrivește tabloului, unele primesc tur liber.": ("The draw is automatic. If the number of teams does not fit the bracket, some receive a bye.", "Le tirage est automatique. Si le nombre d’équipes ne correspond pas au tableau, certaines bénéficient d’un tour exempt.", "El sorteo es automático. Si el número de equipos no encaja en el cuadro, algunos pasan de ronda automáticamente."),
    "Transferul a fost salvat.": ("The transfer was saved.", "Le transfert a été enregistré.", "Se guardó el traspaso."),
    "Transferuri de jucători": ("Player transfers", "Transferts de joueurs", "Traspasos de jugadores"),
    "Transferă jucătorul": ("Transfer player", "Transférer le joueur", "Traspasar jugador"), "Trimite votul": ("Submit vote", "Envoyer le vote", "Enviar voto"),
    "Tur și retur": ("Home and away", "Aller-retour", "Ida y vuelta"),
    "Victorie la masa verde (3–0)": ("Forfeit win (3–0)", "Victoire par forfait (3–0)", "Victoria por incomparecencia (3–0)"),
    "Votează pentru": ("Vote for", "Voter pour", "Votar por"),
    "Votul a fost salvat. Îl poți modifica până la închiderea votului.": ("Your vote was saved. You can change it until voting closes.", "Votre vote a été enregistré. Vous pouvez le modifier jusqu’à la clôture du vote.", "Se guardó tu voto. Puedes cambiarlo hasta que se cierre la votación."),
    "Votul a fost închis și punctajele au fost calculate.": ("Voting has closed and the scores have been calculated.", "Le vote est clos et les scores ont été calculés.", "La votación se cerró y se calcularon las puntuaciones."),
    "Votul este închis de proprietarul sau editorul ligii.": ("Voting is closed by the league owner or editor.", "Le vote est fermé par le propriétaire ou l’éditeur de la ligue.", "El propietario o editor de la liga ha cerrado la votación."),
    "Votul este închis. Membrii ligii nu pot vota până nu îl activezi.": ("Voting is closed. League members cannot vote until you open it.", "Le vote est fermé. Les membres ne peuvent pas voter tant qu’il n’est pas ouvert.", "La votación está cerrada. Los miembros no pueden votar hasta que la abras."),
    "Votul nu este disponibil pentru acest meci.": ("Voting is not available for this match.", "Le vote n’est pas disponible pour ce match.", "La votación no está disponible para este partido."),
    "Votul pentru premiile de sezon este deschis.": ("Season-award voting is open.", "Le vote pour les prix de la saison est ouvert.", "La votación de premios de temporada está abierta."),
    "Votul tău a fost salvat. Îl poți schimba până când meciul este șters.": ("Your vote was saved. You can change it until the match is deleted.", "Votre vote a été enregistré. Vous pouvez le modifier jusqu’à la suppression du match.", "Se guardó tu voto. Puedes cambiarlo hasta que se elimine el partido."),
    "Înapoi la ligile mele": ("Back to my leagues", "Retour à mes ligues", "Volver a mis ligas"),
    "Înapoi la pagina principal": ("Back to the home page", "Retour à la page d’accueil", "Volver a la página principal"),
    "Închide arbitrajul": ("Close refereeing", "Terminer l’arbitrage", "Cerrar arbitraje"),
    "Închide votul și calculează câștigătorii": ("Close voting and calculate the winners", "Clôturer le vote et calculer les gagnants", "Cerrar la votación y calcular los ganadores"),
    "Încă nu există date pentru acest top.": ("There is no data for this leaderboard yet.", "Il n’y a pas encore de données pour ce classement.", "Aún no hay datos para esta clasificación."),
    "Încă nu s-a votat.": ("No votes have been cast yet.", "Aucun vote n’a encore été exprimé.", "Aún no se ha votado."),
    "Înregistrează un meci": ("Record a match", "Enregistrer un match", "Registrar un partido"),
    "Șterge această cupă": ("Delete this cup", "Supprimer cette coupe", "Eliminar esta copa"),
    "Șterge din lot": ("Remove from roster", "Retirer de l’effectif", "Quitar de la plantilla"),
    "Șterge jucător": ("Delete player", "Supprimer le joueur", "Eliminar jugador"),
    "Șterge programul": ("Delete schedule", "Supprimer le calendrier", "Eliminar calendario"),
    "⏸ Pune cronometrul pe pauză": ("⏸ Pause clock", "⏸ Mettre le chronomètre en pause", "⏸ Pausar cronómetro"),
    "▶ Continuă cronometrul": ("▶ Resume clock", "▶ Reprendre le chronomètre", "▶ Reanudar cronómetro"),
    "▶ Pornește repriza a doua": ("▶ Start the second half", "▶ Lancer la deuxième mi-temps", "▶ Iniciar la segunda parte"),
    "➕ Creează o cupă nouă": ("➕ Create a new cup", "➕ Créer une nouvelle coupe", "➕ Crear una copa nueva"),
    "＋ Adaugă eveniment": ("＋ Add event", "＋ Ajouter un événement", "＋ Añadir evento"),
    "🏁 Închide meciul și salvează rezultatul": ("🏁 Finish match and save result", "🏁 Terminer le match et enregistrer le résultat", "🏁 Finalizar partido y guardar resultado"),
    "Înapoi la pagina principală": ("Back to the home page", "Retour à la page d’accueil", "Volver a la página principal"),
    "Acest nume de utilizator este rezervat.": ("This username is reserved.", "Ce nom d’utilisateur est réservé.", "Este nombre de usuario está reservado."),
    "Alege dacă joci la un club profesionist.": ("Choose whether you play for a professional club.", "Indiquez si vous jouez dans un club professionnel.", "Indica si juegas en un club profesional."),
    "Alege exact cinci jucători diferiți, în ordinea preferinței.": ("Choose exactly five different players in preference order.", "Choisissez exactement cinq joueurs différents, par ordre de préférence.", "Elige exactamente cinco jugadores distintos por orden de preferencia."),
    "Alege poziția ta în teren.": ("Choose your position on the field.", "Choisissez votre poste sur le terrain.", "Elige tu posición en el campo."),
    "Alege un jucător care există în lot.": ("Choose a player who is in the roster.", "Choisissez un joueur présent dans l’effectif.", "Elige un jugador que esté en la plantilla."),
    "Codul a fost schimbat. Cere proprietarului codul nou.": ("The code has changed. Ask the owner for the new code.", "Le code a été modifié. Demandez le nouveau code au propriétaire.", "El código ha cambiado. Pide el nuevo código al propietario."),
    "Codul de arbitraj nu este valid.": ("The referee code is invalid.", "Le code d’arbitrage est invalide.", "El código de arbitraje no es válido."),
    "Codul nu mai este valabil pentru acest meci.": ("The code is no longer valid for this match.", "Le code n’est plus valide pour ce match.", "El código ya no es válido para este partido."),
    "Contul nu a fost găsit.": ("The account was not found.", "Le compte est introuvable.", "No se encontró la cuenta."),
    "Data nașterii nu poate fi în viitor.": ("Date of birth cannot be in the future.", "La date de naissance ne peut pas être dans le futur.", "La fecha de nacimiento no puede estar en el futuro."),
    "Există deja o echipă cu acest nume.": ("A team with this name already exists.", "Une équipe portant ce nom existe déjà.", "Ya existe un equipo con este nombre."),
    "Există deja un cont cu această adresă de e-mail.": ("An account with this email address already exists.", "Un compte associé à cette adresse e-mail existe déjà.", "Ya existe una cuenta con esta dirección de correo."),
    "Există deja un cont cu acest nume de utilizator.": ("An account with this username already exists.", "Un compte portant ce nom d’utilisateur existe déjà.", "Ya existe una cuenta con este nombre de usuario."),
    "Fișierul ligii nu mai există.": ("The league file no longer exists.", "Le fichier de la ligue n’existe plus.", "El archivo de la liga ya no existe."),
    "Introdu numele și prenumele.": ("Enter your first and last name.", "Saisissez votre nom et votre prénom.", "Introduce tu nombre y apellidos."),
    "Introdu un nume nou pentru echipă.": ("Enter a new team name.", "Saisissez un nouveau nom d’équipe.", "Introduce un nuevo nombre para el equipo."),
    "Intră în ligă cu un cont sau o invitație pentru a vota.": ("Join the league with an account or invitation to vote.", "Rejoignez la ligue avec un compte ou une invitation pour voter.", "Únete a la liga con una cuenta o invitación para votar."),
    "Invitația a fost revocată.": ("The invitation was revoked.", "L’invitation a été révoquée.", "Se revocó la invitación."),
    "Invitația nu mai este activă.": ("The invitation is no longer active.", "L’invitation n’est plus active.", "La invitación ya no está activa."),
    "Jucătorul ales nu aparține uneia dintre echipele meciului.": ("The selected player does not belong to either team in this match.", "Le joueur sélectionné n’appartient à aucune des équipes de ce match.", "El jugador seleccionado no pertenece a ninguno de los equipos de este partido."),
    "Jucătorul ales nu mai există în lot.": ("The selected player is no longer in the roster.", "Le joueur sélectionné ne figure plus dans l’effectif.", "El jugador seleccionado ya no está en la plantilla."),
    "Jucătorul ales nu mai există în lot. Alege din nou.": ("The selected player is no longer in the roster. Choose again.", "Le joueur sélectionné ne figure plus dans l’effectif. Faites un nouveau choix.", "El jugador seleccionado ya no está en la plantilla. Elígelo de nuevo."),
    "Jucătorul nu mai este în lotul sursă.": ("The player is no longer in the source roster.", "Le joueur ne figure plus dans l’effectif source.", "El jugador ya no está en la plantilla de origen."),
    "Liga a fost creată, dar nu apare încă în lista ligilor contului. Reîncarcă pagina și verifică dacă a fost salvată.": ("The league was created but does not appear in your account yet. Refresh the page and check that it was saved.", "La ligue a été créée, mais n’apparaît pas encore dans votre compte. Actualisez la page et vérifiez qu’elle a été enregistrée.", "La liga se creó, pero aún no aparece en tu cuenta. Actualiza la página y comprueba que se haya guardado."),
    "Liga nu a fost găsită în Supabase sau nu îți aparține.": ("The league was not found in Supabase or does not belong to you.", "La ligue est introuvable dans Supabase ou ne vous appartient pas.", "No se encontró la liga en Supabase o no te pertenece."),
    "Liga nu a putut fi confirmată după salvare.": ("The league could not be confirmed after saving.", "La ligue n’a pas pu être confirmée après l’enregistrement.", "No se pudo confirmar la liga después de guardarla."),
    "Liga nu a putut fi confirmată în Supabase după salvare. Verifică dacă acest cont există în app_users și dacă secretul SUPABASE_SERVICE_ROLE_KEY este corect.": ("The league could not be confirmed in Supabase after saving. Check that the account exists in app_users and that SUPABASE_SERVICE_ROLE_KEY is correct.", "La ligue n’a pas pu être confirmée dans Supabase après l’enregistrement. Vérifiez que le compte existe dans app_users et que SUPABASE_SERVICE_ROLE_KEY est correct.", "No se pudo confirmar la liga en Supabase después de guardarla. Comprueba que la cuenta exista en app_users y que SUPABASE_SERVICE_ROLE_KEY sea correcto."),
    "Liga nu mai există în baza de date.": ("The league no longer exists in the database.", "La ligue n’existe plus dans la base de données.", "La liga ya no existe en la base de datos."),
    "Locația ligii nu corespunde contului tău.": ("The league location does not match your account.", "L’emplacement de la ligue ne correspond pas à votre compte.", "La ubicación de la liga no corresponde a tu cuenta."),
    "Meciul nu mai există.": ("The match no longer exists.", "Le match n’existe plus.", "El partido ya no existe."),
    "Nu mai ai acces la această ligă.": ("You no longer have access to this league.", "Vous n’avez plus accès à cette ligue.", "Ya no tienes acceso a esta liga."),
    "Nu poți vota pentru propriul jucător.": ("You cannot vote for your own player.", "Vous ne pouvez pas voter pour votre propre joueur.", "No puedes votar por tu propio jugador."),
    "Parola trebuie să aibă cel puțin 6 caractere.": ("The password must be at least 6 characters long.", "Le mot de passe doit comporter au moins 6 caractères.", "La contraseña debe tener al menos 6 caracteres."),
    "Poți șterge doar o ligă care îți aparține.": ("You can only delete a league that you own.", "Vous ne pouvez supprimer qu’une ligue qui vous appartient.", "Solo puedes eliminar una liga que te pertenezca."),
    "Premiul selectat nu mai există.": ("The selected award no longer exists.", "Le prix sélectionné n’existe plus.", "El premio seleccionado ya no existe."),
    "Supabase nu a confirmat ștergerea ligii.": ("Supabase did not confirm that the league was deleted.", "Supabase n’a pas confirmé la suppression de la ligue.", "Supabase no confirmó la eliminación de la liga."),
    "Trebuie să intri în ligă înainte să votezi.": ("You must join the league before voting.", "Vous devez rejoindre la ligue avant de voter.", "Debes unirte a la liga antes de votar."),
    "Unul dintre jucătorii aleși nu mai este eligibil pentru acest premiu.": ("One of the selected players is no longer eligible for this award.", "L’un des joueurs sélectionnés n’est plus éligible pour ce prix.", "Uno de los jugadores elegidos ya no puede optar a este premio."),
    "Utilizatorul trebuie să aibă 3–24 caractere și să conțină litere, cifre, _ sau -.": ("The username must be 3–24 characters and contain only letters, numbers, _ or -.", "Le nom d’utilisateur doit comporter de 3 à 24 caractères : lettres, chiffres, _ ou -.", "El nombre de usuario debe tener entre 3 y 24 caracteres y contener letras, números, _ o -."),
    "Votul pentru premii nu este deschis.": ("Award voting is not open.", "Le vote pour les prix n’est pas ouvert.", "La votación de premios no está abierta."),
    "E-mailul/numele de utilizator sau parola nu corespund. Dacă acest cont a fost creat înainte să adaugi e-mailul, conectează-te cu numele de utilizator.": ("The email/username or password is incorrect. If this account was created before you added an email, sign in with your username.", "L’adresse e-mail, le nom d’utilisateur ou le mot de passe est incorrect. Si le compte a été créé avant l’ajout d’une adresse e-mail, connectez-vous avec votre nom d’utilisateur.", "El correo, el nombre de usuario o la contraseña no coinciden. Si creaste esta cuenta antes de añadir un correo, inicia sesión con tu nombre de usuario."),
    "Premiile individuale care nu se acordă automat se stabilesc prin vot: fiecare votant ordonează cinci jucători, iar punctele 5–4–3–2–1 se calculează la închiderea votului.": ("Individual awards that are not automatic are decided by vote: each voter ranks five players, and points 5–4–3–2–1 are calculated when voting closes.", "Les prix individuels non automatiques sont attribués par vote : chaque votant classe cinq joueurs et les points 5–4–3–2–1 sont calculés à la clôture du vote.", "Los premios individuales no automáticos se deciden por votación: cada votante ordena cinco jugadores y los puntos 5–4–3–2–1 se calculan al cerrar la votación."),
    "Supabase nu este conectat: ligile se salvează doar local și se pot pierde când aplicația repornește. Verifică SUPABASE_URL și SUPABASE_SERVICE_ROLE_KEY în Secrets.": ("Supabase is not connected: leagues are stored locally and may be lost when the app restarts. Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in Secrets.", "Supabase n’est pas connecté : les ligues sont enregistrées localement et peuvent être perdues au redémarrage. Vérifiez SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY dans les Secrets.", "Supabase no está conectado: las ligas se guardan localmente y podrían perderse al reiniciar la aplicación. Revisa SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY en Secrets."),
    "Timpul suplimentar s-a scurs. Cronometrul continuă să ruleze; înregistrează ce se mai întâmplă, apoi închide meciul.": ("Added time has expired. The clock keeps running; record any further events, then finish the match.", "Le temps additionnel est écoulé. Le chronomètre continue ; enregistrez les événements éventuels, puis terminez le match.", "El tiempo añadido ha terminado. El cronómetro sigue en marcha; registra lo que ocurra y después finaliza el partido."),
    "Timpul suplimentar s-a scurs. Cronometrul continuă să ruleze; înregistrează ce se mai întâmplă, apoi închide repriza.": ("Added time has expired. The clock keeps running; record any further events, then end the half.", "Le temps additionnel est écoulé. Le chronomètre continue ; enregistrez les événements éventuels, puis terminez la mi-temps.", "El tiempo añadido ha terminado. El cronómetro sigue en marcha; registra lo que ocurra y después termina la parte."),
    "Înapoi la pagina principal": ("Back to the home page", "Retour à la page d’accueil", "Volver a la página principal"),
}
for _source, (_en, _fr, _es) in _EXTRA_TRANSLATIONS.items():
    UI_TRANSLATIONS["en"][_source] = _en
    UI_TRANSLATIONS["fr"][_source] = _fr
    UI_TRANSLATIONS["es"][_source] = _es

for _source, (_en, _fr, _es) in {
    "Anulează": ("Cancel", "Annuler", "Cancelar"),
    "Da, șterge cupa": ("Yes, delete the cup", "Oui, supprimer la coupe", "Sí, eliminar la copa"),
    "Gazdă": ("Home", "Domicile", "Local"), "Jucători": ("Players", "Joueurs", "Jugadores"),
    "Oaspeți": ("Away", "Extérieur", "Visitante"), "Păstrează cupa": ("Keep cup", "Conserver la coupe", "Conservar la copa"),
    "Revocă": ("Revoke", "Révoquer", "Revocar"), "Salvează rolul": ("Save role", "Enregistrer le rôle", "Guardar rol"),
    "Șterge": ("Delete", "Supprimer", "Eliminar"), "⏸ Pauză": ("⏸ Pause", "⏸ Pause", "⏸ Pausa"),
    "▶ Continuă prelungirile": ("▶ Continue extra time", "▶ Reprendre les prolongations", "▶ Continuar la prórroga"),
    "Cronometru": ("Match clock", "Chronomètre", "Cronómetro"),
    "Echipe": ("Teams", "Équipes", "Equipos"), "Meciuri": ("Matches", "Matchs", "Partidos"),
    "Rol": ("Role", "Rôle", "Rol"), "Runde": ("Rounds", "Tours", "Rondas"),
    "Stare": ("Status", "État", "Estado"), "Progresul cupei": ("Cup progress", "Progression de la coupe", "Progreso de la copa"),
}.items():
    UI_TRANSLATIONS["en"][_source] = _en
    UI_TRANSLATIONS["fr"][_source] = _fr
    UI_TRANSLATIONS["es"][_source] = _es

UI_PARTIAL_TRANSLATIONS = {
    "en": {"Voturi înregistrate:": "Votes recorded:", "Vot pentru ": "Vote for ",
        "Locul ": "Place ", " puncte": " points", "Etapa ": "Round ", "Minutul meciului:": "Match minute:",
        "Schimbare:": "Substitution:", "Schimbări:": "Substitutions:", "Schimbări retur:": "Second-leg substitutions:",
        "Scor agregat după 90′:": "Aggregate score after 90′:", "Scor agregat:": "Aggregate score:",
        "se califică ": "advances ", "câștigă ": "wins ", "câștigă **": "wins **", "Partajată de ": "Shared by ",
        "Partajată de @": "Shared by @", "Proprietar: ": "Owner: ", " · Acces: ": " · Access: ",
        "Profilul meu · ": "My profile · ", "Invitație pentru ": "Invitation for ", "jucător în ligă": "league player",
        "Invitat ca jucător:": "Invited as player:", " · jucători": " · players", " · decise": " · decided",
        "Nu am putut salva votul:": "Could not save vote:", "Nu am putut salva alegerea:": "Could not save selection:",
        "Nu am putut salva asocierea:": "Could not save player selection:", "Detaliu:": "Details:",
        "Nu am putut încărca detaliile pentru liga": "Could not load league details for",
        "este acum liga ta preferată.": "is now your favorite league.", "Datele au rămas salvate.": "The data remains saved.",
        "a fost redenumită.": "was renamed.", "a fost salvat.": "was saved.", "a fost importată.": "was imported.",
        "Fișierul nu este un JSON de ligă valid:": "The file is not a valid league JSON:",
        "Statisticile lui ": "Statistics for ", " au fost actualizate.": " were updated.",
        "Rezultatul va fi ": "The result will be ", "Confirmi ștergerea cupei": "Confirm deletion of cup",
        "Acțiunea nu poate fi anulată.": "This action cannot be undone.", "Meciul ": "Match ",
        "Returul ": "Second leg ", "Turul ": "First leg ", "Finala · ": "Final · ",
        "Se califică ": "Advances ", "Perecherea folosește clasamentul actual al ligii.": "The pairing uses the current league standings.",
        "Sugestie din datele actuale:": "Suggestion based on current data:", "Câștigător automat:": "Automatic winner:",
        "Sezonul este încă în desfășurare:": "The season is still in progress:", " meciuri de ligă și ": " league matches and ",
        " cupe fără câștigător.": " cups without a winner.", "Poți acorda premiile oricând.": "You can award the prizes at any time.",
        "Rolul tău:": "Your role:", "Alegerea profilului:": "Profile selection:", " a câștigat ": " won ",
        "Închide": "Close", "Deschide": "Open", "Câștigător automat:": "Automatic winner:",
        "Tur:": "First leg:", "Retur:": "Second leg:", "Finală propusă:": "Proposed final:",
        "Preferată": "Favorite", "⭐ Preferată": "⭐ Favorite", "· Ascunsă": "· Hidden",
        " echipe · ": " teams · ", " meciuri · ": " matches · ", "creată de tine": "created by you",
        "partajată": "shared", "Partajată": "Shared", "Elimină": "Hide", "Afișează": "Show",
        "Da, afișeaz-o": "Yes, show it", "Da, elimin-o din listă": "Yes, hide it from the list",
        "Șterge": "Delete", "Anulează": "Cancel", "Nu am putut încărca detaliile pentru liga «": "Could not load details for league “",
        "»? Datele ei nu vor fi șterse.": "”? Its data will not be deleted.", "Datele ei nu vor fi șterse.": "Its data will not be deleted.",
        "Ai intrat ca jucător:": "You joined as a player:", " jucători": " players", "Liga nu a putut fi ștearsă:": "The league could not be deleted:", "avansează cu tur liber.": "advances with a bye.",
        "Clasamente, meciuri și cupe într-un singur loc": "Standings, matches and cups in one place", "Partener · link afiliat": "Partner · affiliate link",
        "Biciclete, piese și accesorii pentru următoarea ta aventură": "Bikes, parts and accessories for your next adventure", "Descoperă magazinul": "Explore the store",
        "Vizitează magazinul Piese-Biciclete.eu — link afiliat": "Visit the Piese-Biciclete.eu store — affiliate link"},
    "fr": {"Voturi înregistrate:": "Votes enregistrés :", "Vot pentru ": "Vote pour ",
        "Locul ": "Place ", " puncte": " points", "Etapa ": "Journée ", "Minutul meciului:": "Minute du match :",
        "Schimbare:": "Remplacement :", "Schimbări:": "Remplacements :", "Schimbări retur:": "Remplacements du match retour :",
        "Scor agregat după 90′:": "Score cumulé après 90′ :", "Scor agregat:": "Score cumulé :",
        "se califică ": "se qualifie ", "câștigă ": "remporte ", "câștigă **": "remporte **", "Partajată de ": "Partagée par ",
        "Partajată de @": "Partagée par @", "Proprietar: ": "Propriétaire : ", " · Acces: ": " · Accès : ",
        "Profilul meu · ": "Mon profil · ", "Invitație pentru ": "Invitation pour ", "jucător în ligă": "joueur de la ligue",
        "Invitat ca jucător:": "Invité en tant que joueur :", " · jucători": " · joueurs", " · decise": " · décidés",
        "Nu am putut salva votul:": "Impossible d’enregistrer le vote :", "Nu am putut salva alegerea:": "Impossible d’enregistrer le choix :",
        "Nu am putut salva asocierea:": "Impossible d’enregistrer le choix du joueur :", "Detaliu:": "Détails :",
        "Nu am putut încărca detaliile pentru liga": "Impossible de charger les détails de la ligue",
        "este acum liga ta preferată.": "est maintenant votre ligue favorite.", "Datele au rămas salvate.": "Les données restent enregistrées.",
        "a fost redenumită.": "a été renommée.", "a fost salvat.": "a été enregistré.", "a fost importată.": "a été importée.",
        "Fișierul nu este un JSON de ligă valid:": "Le fichier n’est pas un JSON de ligue valide :",
        "Statisticile lui ": "Statistiques de ", " au fost actualizate.": " ont été mises à jour.",
        "Rezultatul va fi ": "Le résultat sera ", "Confirmi ștergerea cupei": "Confirmer la suppression de la coupe",
        "Acțiunea nu poate fi anulată.": "Cette action est irréversible.", "Meciul ": "Match ",
        "Returul ": "Match retour ", "Turul ": "Match aller ", "Finala · ": "Finale · ",
        "Se califică ": "Se qualifie ", "Perecherea folosește clasamentul actual al ligii.": "L’affiche utilise le classement actuel de la ligue.",
        "Sugestie din datele actuale:": "Suggestion basée sur les données actuelles :", "Câștigător automat:": "Vainqueur automatique :",
        "Sezonul este încă în desfășurare:": "La saison est toujours en cours :", " meciuri de ligă și ": " matchs de ligue et ",
        " cupe fără câștigător.": " coupes sans vainqueur.", "Poți acorda premiile oricând.": "Vous pouvez attribuer les prix à tout moment.",
        "Rolul tău:": "Votre rôle :", "Alegerea profilului:": "Choix du profil :", " a câștigat ": " a remporté ",
        "Închide": "Fermer", "Deschide": "Ouvrir", "Tur:": "Aller :", "Retur:": "Retour :",
        "Finală propusă:": "Finale proposée :", "Preferată": "Favorite", "⭐ Preferată": "⭐ Favorite",
        "· Ascunsă": "· Masquée", " echipe · ": " équipes · ", " meciuri · ": " matchs · ",
        "creată de tine": "créée par vous", "partajată": "partagée", "Partajată": "Partagée",
        "Elimină": "Masquer", "Afișează": "Afficher", "Da, afișeaz-o": "Oui, l’afficher",
        "Da, elimin-o din listă": "Oui, la masquer de la liste", "Șterge": "Supprimer", "Anulează": "Annuler",
        "Nu am putut încărca detaliile pentru liga «": "Impossible de charger les détails de la ligue «",
        "»? Datele ei nu vor fi șterse.": "». Ses données ne seront pas supprimées.", "Datele ei nu vor fi șterse.": "Ses données ne seront pas supprimées.",
        "Ai intrat ca jucător:": "Vous avez rejoint comme joueur :", " jucători": " joueurs", "Liga nu a putut fi ștearsă:": "Impossible de supprimer la ligue :", "avansează cu tur liber.": "passe au tour suivant sans jouer.",
        "Clasamente, meciuri și cupe într-un singur loc": "Classements, matchs et coupes au même endroit", "Partener · link afiliat": "Partenaire · lien affilié",
        "Biciclete, piese și accesorii pentru următoarea ta aventură": "Vélos, pièces et accessoires pour votre prochaine aventure", "Descoperă magazinul": "Découvrir la boutique",
        "Vizitează magazinul Piese-Biciclete.eu — link afiliat": "Visiter la boutique Piese-Biciclete.eu — lien affilié"},
    "es": {"Voturi înregistrate:": "Votos registrados:", "Vot pentru ": "Votar por ",
        "Locul ": "Puesto ", " puncte": " puntos", "Etapa ": "Jornada ", "Minutul meciului:": "Minuto del partido:",
        "Schimbare:": "Cambio:", "Schimbări:": "Cambios:", "Schimbări retur:": "Cambios de la vuelta:",
        "Scor agregat după 90′:": "Marcador global tras 90′:", "Scor agregat:": "Marcador global:",
        "se califică ": "se clasifica ", "câștigă ": "gana ", "câștigă **": "gana **", "Partajată de ": "Compartida por ",
        "Partajată de @": "Compartida por @", "Proprietar: ": "Propietario: ", " · Acces: ": " · Acceso: ",
        "Profilul meu · ": "Mi perfil · ", "Invitație pentru ": "Invitación para ", "jucător în ligă": "jugador de la liga",
        "Invitat ca jucător:": "Invitado como jugador:", " · jucători": " · jugadores", " · decise": " · decididos",
        "Nu am putut salva votul:": "No se pudo guardar el voto:", "Nu am putut salva alegerea:": "No se pudo guardar la selección:",
        "Nu am putut salva asocierea:": "No se pudo guardar la selección del jugador:", "Detaliu:": "Detalles:",
        "Nu am putut încărca detaliile pentru liga": "No se pudieron cargar los detalles de la liga",
        "este acum liga ta preferată.": "ahora es tu liga favorita.", "Datele au rămas salvate.": "Los datos siguen guardados.",
        "a fost redenumită.": "cambió de nombre.", "a fost salvat.": "se guardó.", "a fost importată.": "se importó.",
        "Fișierul nu este un JSON de ligă valid:": "El archivo no es un JSON de liga válido:",
        "Statisticile lui ": "Estadísticas de ", " au fost actualizate.": " se actualizaron.",
        "Rezultatul va fi ": "El resultado será ", "Confirmi ștergerea cupei": "¿Confirmas que quieres eliminar la copa",
        "Acțiunea nu poate fi anulată.": "Esta acción no se puede deshacer.", "Meciul ": "Partido ",
        "Returul ": "La vuelta ", "Turul ": "La ida ", "Finala · ": "Final · ",
        "Se califică ": "Se clasifica ", "Perecherea folosește clasamentul actual al ligii.": "El emparejamiento usa la clasificación actual de la liga.",
        "Sugestie din datele actuale:": "Sugerencia basada en los datos actuales:", "Câștigător automat:": "Ganador automático:",
        "Sezonul este încă în desfășurare:": "La temporada sigue en curso:", " meciuri de ligă și ": " partidos de liga y ",
        " cupe fără câștigător.": " copas sin ganador.", "Poți acorda premiile oricând.": "Puedes conceder los premios cuando quieras.",
        "Rolul tău:": "Tu rol:", "Alegerea profilului:": "Selección del perfil:", " a câștigat ": " ganó ",
        "Închide": "Cerrar", "Deschide": "Abrir", "Tur:": "Ida:", "Retur:": "Vuelta:",
        "Finală propusă:": "Final propuesta:", "Preferată": "Favorita", "⭐ Preferată": "⭐ Favorita",
        "· Ascunsă": "· Oculta", " echipe · ": " equipos · ", " meciuri · ": " partidos · ",
        "creată de tine": "creada por ti", "partajată": "compartida", "Partajată": "Compartida",
        "Elimină": "Ocultar", "Afișează": "Mostrar", "Da, afișeaz-o": "Sí, mostrarla",
        "Da, elimin-o din listă": "Sí, ocultarla de la lista", "Șterge": "Eliminar", "Anulează": "Cancelar",
        "Nu am putut încărca detaliile pentru liga «": "No se pudieron cargar los detalles de la liga «",
        "»? Datele ei nu vor fi șterse.": "». Sus datos no se eliminarán.", "Datele ei nu vor fi șterse.": "Sus datos no se eliminarán.",
        "Ai intrat ca jucător:": "Has entrado como jugador:", " jucători": " jugadores", "Liga nu a putut fi ștearsă:": "No se pudo eliminar la liga:", "avansează cu tur liber.": "avanza sin jugar.",
        "Clasamente, meciuri și cupe într-un singur loc": "Clasificaciones, partidos y copas en un solo lugar", "Partener · link afiliat": "Socio · enlace de afiliado",
        "Biciclete, piese și accesorii pentru următoarea ta aventură": "Bicicletas, piezas y accesorios para tu próxima aventura", "Descoperă magazinul": "Descubre la tienda",
        "Vizitează magazinul Piese-Biciclete.eu — link afiliat": "Visita la tienda Piese-Biciclete.eu — enlace de afiliado"},
}

for _language, _title in {
    "zh": "足球联赛管理器", "hi": "फुटबॉल लीग मैनेजर", "fr": "Gestionnaire de ligue de football",
    "bn": "ফুটবল লিগ ম্যানেজার", "pt": "Gerenciador de Ligas de Futebol",
    "id": "Manajer Liga Sepak Bola", "ru": "Менеджер футбольной лиги", "de": "Fußball-Liga-Manager",
    "ja": "サッカーリーグ管理", "ar": "مدير دوري كرة القدم", "ur": "فٹبال لیگ مینیجر",
    "pcm": "Football League Manager", "arz": "مدير دوري الكورة",
}.items():
    UI_TRANSLATIONS[_language]["Managerul ligii de fotbal"] = _title
for _language in list(UI_TRANSLATIONS):
    if _language not in {"en", "fr", "es"}:
        UI_TRANSLATIONS.pop(_language, None)


def tr(text):
    language = st.session_state.get("ui_language", "ro")
    phrase = str(text)
    if language == "ro":
        return phrase
    translated = UI_TRANSLATIONS.get(language, {}).get(phrase)
    if translated is None:
        translated = UI_TRANSLATIONS.get("en", {}).get(phrase)
    if translated is not None:
        return translated
    partials = UI_PARTIAL_TRANSLATIONS.get(language, UI_PARTIAL_TRANSLATIONS["en"])
    for source in sorted(partials, key=len, reverse=True):
        if source in phrase:
            phrase = phrase.replace(source, partials[source])
    return phrase


def language_label(language_code):
    return next((label for label, code in LANGUAGE_OPTIONS.items() if code == language_code), "Română")


def render_language_selector(username=None, key="language_selector"):
    current = st.session_state.get("ui_language", "ro")
    selected = st.selectbox(tr("Limba"), list(LANGUAGE_OPTIONS),
        index=list(LANGUAGE_OPTIONS.values()).index(current) if current in LANGUAGE_OPTIONS.values() else 0,
        key=key)
    selected_code = LANGUAGE_OPTIONS[selected]
    if selected_code != current:
        st.session_state["ui_language"] = selected_code
        if username:
            users = load_users()
            account = users.get(username.casefold())
            if account is not None:
                account["limba"] = selected_code
                save_users(users)
        st.rerun()
    if selected_code in {"ar", "arz", "ur"}:
        st.markdown("<style>[data-testid='stAppViewContainer'],[data-testid='stSidebar']{direction:rtl;text-align:right} [data-testid='stMarkdownContainer'],[data-testid='stWidgetLabel']{text-align:right}</style>", unsafe_allow_html=True)


def install_ui_translations():
    """Translate Streamlit labels and messages centrally as catalogs grow."""
    method_names = ("title", "header", "subheader", "caption", "markdown", "write", "info",
        "warning", "error", "success", "button", "text_input", "text_area", "number_input",
        "selectbox", "multiselect", "radio", "checkbox", "form_submit_button", "expander",
        "tabs", "download_button", "file_uploader", "metric", "date_input", "progress")

    def translate_value(value):
        if isinstance(value, str):
            return tr(value)
        if isinstance(value, (list, tuple)):
            return type(value)(translate_value(item) for item in value)
        return value

    for method_name in method_names:
        original = getattr(st, method_name, None)
        if not callable(original) or getattr(original, "_league_i18n", False):
            continue

        def localized(*args, _original=original, _name=method_name, **kwargs):
            if args:
                args = (translate_value(args[0]), *args[1:])
            elif "label" in kwargs:
                kwargs["label"] = translate_value(kwargs["label"])
            if _name == "tabs" and args:
                args = (translate_value(args[0]), *args[1:])
            if _name in {"selectbox", "multiselect", "radio"} and "format_func" not in kwargs:
                kwargs["format_func"] = tr
            return _original(*args, **kwargs)

        localized._league_i18n = True
        setattr(st, method_name, localized)

BASE_DIR = Path(os.environ.get("LIGA_DATA_DIR", Path(__file__).resolve().parent / "ligi"))
APP_DIR = Path(__file__).resolve().parent
USERS_FILE = Path(os.environ.get("LIGA_USERS_FILE", APP_DIR / "utilizatori.json"))
PASSWORD_ITERATIONS = 200_000
RESERVED_USERNAMES = {"con", "prn", "aux", "nul", "admin"} | \
    {f"com{i}" for i in range(1, 10)} | {f"lpt{i}" for i in range(1, 10)}
REMEMBER_COOKIE = "liga_remember_me"
REMEMBER_DAYS = 30


def _supabase_settings():
    try:
        return (str(st.secrets.get("SUPABASE_URL", "")).strip(),
                str(st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")).strip())
    except Exception:
        return "", ""


SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY = _supabase_settings()
SUPABASE_ENABLED = bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


@st.cache_resource
def supabase_client():
    if not SUPABASE_ENABLED:
        return None
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def db_league_path(owner, league_id):
    return BASE_DIR / str(owner) / f"{league_id}.json"


def is_db_league_path(path):
    if not SUPABASE_ENABLED:
        return False
    try:
        uuid.UUID(Path(path).stem)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def db_league_id(path):
    return Path(path).stem


def all_db_league_rows():
    return supabase_client().table("app_leagues").select(
        "id,owner_username,nume,data,updated_at").execute().data or []


def normalizeaza_date(data):
    data.setdefault("nume_liga", "Liga mea")
    settings = data.get("setari_liga")
    if not isinstance(settings, dict):
        settings = {}
    settings.setdefault("motm_voting_mode", "no_players")
    settings.setdefault("award_voting_mode", "direct")
    settings.setdefault("award_voting_open", False)
    settings.setdefault("cup_leg_format", "single")
    settings.setdefault("cup_tie_resolution", "penalties")
    settings.setdefault("supercup_leg_format", "single")
    settings.setdefault("supercup_tie_resolution", "penalties")
    settings.setdefault("substitution_rule", "5_no_return")
    data["setari_liga"] = settings
    for key, default in (("echipe", {}), ("istoric_meciuri", []), ("program", []),
                         ("transferuri", []), ("cupe", []), ("invitatii", []), ("sterse", []),
                         ("membri", []), ("selectii_membri", {}), ("premii_alese", {}),
                         ("voturi_premii", {})):
        if not isinstance(data.get(key), type(default)):
            data[key] = copy.deepcopy(default)
    for team in data["echipe"].values():
        for key, value in STATS_ECHIPA.items():
            team.setdefault(key, value)
        team.setdefault("jucatori", {})
        for player, stats in list(team["jucatori"].items()):
            if not isinstance(stats, dict):
                stats = {}
                team["jucatori"][player] = stats
            for key, value in STATS_JUCATOR.items():
                stats.setdefault(key, value)
            stats.setdefault("pozitie", "")
    for match in data["istoric_meciuri"]:
        match.setdefault("id", uuid.uuid4().hex[:8])
        match.setdefault("etapa", None)
        match.setdefault("evenimente", [])
        match.setdefault("goluri_e1", 0)
        match.setdefault("goluri_e2", 0)
    for fixture in data["program"]:
        fixture.setdefault("id", uuid.uuid4().hex[:8])
        fixture.setdefault("meci_id", None)
    for cup in data["cupe"]:
        cup.setdefault("id", uuid.uuid4().hex[:8])
        cup.setdefault("nume", "Cupa")
        cup.setdefault("tur_retur", False)
        cup.setdefault("runde", [])
        cup.setdefault("status", "în desfășurare")
        cup.setdefault("castigatoare", None)
        for round_data in cup["runde"]:
            round_data.setdefault("nume", "Runda")
            for slot in round_data.get("meciuri", []):
                slot.setdefault("meci_retur", None)
            for slot in round_data.get("meciuri", []):
                slot.setdefault("id", uuid.uuid4().hex[:8])
                slot.setdefault("e1", None)
                slot.setdefault("e2", None)
                slot.setdefault("meci", None)
                slot.setdefault("castigator", None)
                slot.setdefault("penalti", False)
    return data


def safe_slug(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "liga"


def load_users():
    if SUPABASE_ENABLED:
        rows = supabase_client().table("app_users").select("username,data").execute().data or []
        return {str(row["username"]).strip().casefold(): row.get("data") or {}
                for row in rows if row.get("username")}
    if not USERS_FILE.exists():
        return {}
    try:
        payload = json.loads(USERS_FILE.read_text(encoding="utf-8"))
        users = payload.get("utilizatori", {}) if isinstance(payload, dict) else {}
        return {str(username).strip().casefold(): record
                for username, record in users.items() if username}
    except (OSError, json.JSONDecodeError):
        return {}


def save_users(users):
    if SUPABASE_ENABLED:
        table = supabase_client().table("app_users")
        # `users` is a snapshot read earlier in this request. Deleting rows that
        # are absent from it can erase accounts created by another session.
        # Account removal is not part of this flow, so only upsert supplied rows.
        if users:
            table.upsert([{"username": username, "data": record}
                          for username, record in users.items()], on_conflict="username").execute()
        return
    temp = USERS_FILE.with_suffix(".json.tmp")
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp.write_text(json.dumps({"utilizatori": users}, ensure_ascii=False, indent=2), encoding="utf-8")
    if USERS_FILE.exists():
        shutil.copy2(USERS_FILE, USERS_FILE.with_suffix(".json.bak"))
    os.replace(temp, USERS_FILE)


def cookie_is_secure():
    try:
        forwarded = st.context.headers.get("X-Forwarded-Proto", "")
        return "https" in str(forwarded).casefold()
    except Exception:
        return False


def browser_cookie(cookie_manager, name):
    value = cookie_manager.get(name)
    if value is not None:
        return value
    try:
        return st.context.cookies.get(name)
    except Exception:
        return None


def delete_browser_cookie(cookie_manager, name, key_prefix):
    value = browser_cookie(cookie_manager, name)
    if value is None:
        return
    # CookieManager.delete removes the value from its local map before sending
    # the delete request to the browser; seed it if the request cookie loaded first.
    cookies = getattr(cookie_manager, "cookies", None)
    if isinstance(cookies, dict):
        cookies[name] = value
    cookie_manager.delete(name, key=f"{key_prefix}_{uuid.uuid4().hex}")


def remember_account(cookie_manager, username):
    users = load_users()
    record = users.get(username)
    if not record:
        return
    now = int(dt.datetime.now().timestamp())
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    sessions = record.setdefault("remember_tokens", {})
    if not isinstance(sessions, dict):
        sessions = record["remember_tokens"] = {}
    sessions = {key: expiry for key, expiry in sessions.items()
                if isinstance(expiry, (int, float)) and expiry > now}
    sessions[token_hash] = now + REMEMBER_DAYS * 24 * 60 * 60
    while len(sessions) > 10:
        oldest = min(sessions, key=sessions.get)
        sessions.pop(oldest, None)
    record["remember_tokens"] = sessions
    save_users(users)
    cookie_manager.set(REMEMBER_COOKIE, f"{username}.{raw_token}",
        key=f"remember_login_{uuid.uuid4().hex}", path="/",
        expires_at=dt.datetime.now() + dt.timedelta(days=REMEMBER_DAYS),
        max_age=REMEMBER_DAYS * 24 * 60 * 60, secure=cookie_is_secure(), same_site="strict")
    st.session_state["pending_remember_login"] = {
        "username": username, "token_hash": token_hash}


def revoke_remembered_account(cookie_manager):
    username = st.session_state.pop("remembered_username", None)
    token_hash = st.session_state.pop("remembered_token_hash", None)
    if username and token_hash:
        users = load_users()
        record = users.get(username, {})
        sessions = record.get("remember_tokens", {})
        if token_hash in sessions:
            sessions.pop(token_hash, None)
            save_users(users)
    delete_browser_cookie(cookie_manager, REMEMBER_COOKIE, "forget_login")


def restore_remembered_account(cookie_manager):
    value = browser_cookie(cookie_manager, REMEMBER_COOKIE)
    if not value:
        return
    try:
        username, raw_token = str(value).split(".", 1)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        record = load_users().get(username, {})
        expiry = record.get("remember_tokens", {}).get(token_hash)
        if expiry and float(expiry) > dt.datetime.now().timestamp():
            st.session_state["user_key"] = username
            st.session_state["ui_language"] = record.get("limba", "ro")
            st.session_state["remembered_username"] = username
            st.session_state["remembered_token_hash"] = token_hash
            return
    except (ValueError, TypeError, AttributeError):
        pass
    delete_browser_cookie(cookie_manager, REMEMBER_COOKIE, "clear_invalid_login")


def finish_pending_remember_login(cookie_manager):
    pending = st.session_state.get("pending_remember_login")
    if not pending:
        return False
    value = browser_cookie(cookie_manager, REMEMBER_COOKIE)
    try:
        username, raw_token = str(value).split(".", 1)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    except (AttributeError, ValueError):
        return False
    if username != pending.get("username") or not hmac.compare_digest(
            token_hash, str(pending.get("token_hash", ""))):
        return False
    st.session_state["user_key"] = username
    st.session_state["ui_language"] = load_users().get(username, {}).get("limba", "ro")
    st.session_state["remembered_username"] = username
    st.session_state["remembered_token_hash"] = token_hash
    st.session_state.pop("pending_remember_login", None)
    return True


def password_hash(password, salt=None, iterations=PASSWORD_ITERATIONS):
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return salt.hex(), digest.hex()


def verify_password(record, password):
    try:
        _, digest = password_hash(password, bytes.fromhex(record["sare"]),
                                  int(record.get("iteratii", PASSWORD_ITERATIONS)))
        return hmac.compare_digest(digest, record["hash"])
    except (KeyError, ValueError, TypeError):
        return False


def create_account(username, email, password, name, birthday, plays_professional, position):
    username = username.strip()
    normalized_username = username.lower()
    normalized_email = email.strip().casefold()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{2,23}", username):
        raise ValueError("Utilizatorul trebuie să aibă 3–24 caractere și să conțină litere, cifre, _ sau -.")
    if normalized_username in RESERVED_USERNAMES:
        raise ValueError("Acest nume de utilizator este rezervat.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized_email):
        raise ValueError("Introdu o adresă de e-mail validă.")
    if len(password) < 6:
        raise ValueError("Parola trebuie să aibă cel puțin 6 caractere.")
    if not name.strip():
        raise ValueError("Introdu numele și prenumele.")
    if birthday > dt.date.today():
        raise ValueError("Data nașterii nu poate fi în viitor.")
    if plays_professional not in ("Da", "Nu"):
        raise ValueError("Alege dacă joci la un club profesionist.")
    if position not in POZITII_FOTBAL:
        raise ValueError("Alege poziția ta în teren.")
    users = load_users()
    if normalized_username in users:
        raise ValueError("Există deja un cont cu acest nume de utilizator.")
    if any(str(record.get("email", "")).strip().casefold() == normalized_email
           for record in users.values()):
        raise ValueError("Există deja un cont cu această adresă de e-mail.")
    salt, digest = password_hash(password)
    users[normalized_username] = {"nume": name.strip(), "email": normalized_email,
        "data_nasterii": birthday.strftime("%d.%m.%Y"),
        "joaca_fotbal": plays_professional, "pozitie": position, "sare": salt, "hash": digest,
        "iteratii": PASSWORD_ITERATIONS, "dispozitive": [], "selectii_ligi": {}, "limba": "ro",
        "creat": dt.date.today().strftime("%d.%m.%Y")}
    save_users(users)
    return normalized_username


def get_user_leagues(username, include_hidden=False):
    users = load_users()
    account = users.get(username.casefold(), {})
    hidden = set(account.get("ligii_ascunse", [])) if isinstance(account, dict) else set()

    def favorite_first(entries):
        favorite = account.get("liga_preferata") if isinstance(account, dict) else None
        return sorted(entries, key=lambda entry: league_key(entry) != favorite)

    if SUPABASE_ENABLED:
        entries = []
        for row in all_db_league_rows():
            owner = row.get("owner_username", "")
            data = row.get("data") or {}
            role = "owner" if owner.casefold() == username.casefold() else None
            if role is None:
                member = next((m for m in data.get("membri", [])
                               if str(m.get("username", "")).casefold() == username.casefold()
                               and m.get("activ", True)), None)
                if member:
                    role = member.get("rol", "vizitator")
            if role:
                entries.append({"path": db_league_path(owner, row["id"]), "role": role,
                                "owner": owner, "updated_at": row.get("updated_at", "")})
        entries.sort(key=lambda entry: entry.get("updated_at", ""), reverse=True)
        entries = favorite_first(entries)
        if include_hidden:
            return entries
        return [entry for entry in entries if league_key(entry) not in hidden]
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    entries = []
    own_dir = BASE_DIR / username
    own_dir.mkdir(parents=True, exist_ok=True)
    for path in own_dir.glob("*.json"):
        entries.append({"path": path, "role": "owner", "owner": username})
    for folder in BASE_DIR.iterdir():
        if not folder.is_dir() or folder.name.startswith("_") or folder.name.casefold() == username.casefold():
            continue
        for path in folder.glob("*.json"):
            try:
                data = load_league(path)
            except ValueError:
                continue
            access = next((m for m in data.get("membri", [])
                           if str(m.get("username", "")).casefold() == username.casefold()), None)
            if access and access.get("activ", True):
                entries.append({"path": path, "role": access.get("rol", "vizitator"), "owner": folder.name})
    entries.sort(key=lambda entry: entry["path"].stat().st_mtime if Path(entry["path"]).exists() else 0,
                 reverse=True)
    entries = favorite_first(entries)
    if include_hidden:
        return entries
    return [entry for entry in entries if league_key(entry) not in hidden]


def league_key(entry):
    return f"{entry['owner']}/{entry['path'].name}"


def find_invitation(token):
    if not token:
        return None
    if SUPABASE_ENABLED:
        for row in all_db_league_rows():
            path, owner = db_league_path(row["owner_username"], row["id"]), row["owner_username"]
            data = normalizeaza_date(row.get("data") or {})
            for invite in data.get("invitatii", []):
                if invite.get("activ", True) and hmac.compare_digest(
                        str(invite.get("token", "")), str(token)):
                    role = "vizitator" if invite.get("tip", "spectator") == "spectator" else invite.get("rol", "vizitator")
                    return {"path": path, "owner": owner, "role": role,
                            "invitation": invite, "data": data, "access_method": "legacy"}
        return None
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    for folder in BASE_DIR.iterdir():
        if not folder.is_dir() or folder.name.startswith("_"):
            continue
        for path in folder.glob("*.json"):
            try:
                data = load_league(path)
            except ValueError:
                continue
            for invite in data.get("invitatii", []):
                if (invite.get("activ", True)
                        and hmac.compare_digest(str(invite.get("token", "")), str(token))):
                    role = "vizitator" if invite.get("tip", "spectator") == "spectator" else invite.get("rol", "vizitator")
                    return {"path": path, "owner": folder.name, "role": role,
                            "invitation": invite, "data": data, "access_method": "legacy"}
    return None


def normalize_access_code(code):
    return "".join(char for char in str(code or "").upper() if char.isalnum())


def new_access_code():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    raw = "".join(secrets.choice(alphabet) for _ in range(12))
    return "-".join(raw[index:index + 4] for index in range(0, 12, 4))


def new_league_access_codes():
    return {"spectator": new_access_code(), "editor": new_access_code()}


def find_access_code(code):
    normalized = normalize_access_code(code)
    if len(normalized) != 12:
        return None
    if SUPABASE_ENABLED:
        for row in all_db_league_rows():
            path, owner = db_league_path(row["owner_username"], row["id"]), row["owner_username"]
            data = normalizeaza_date(row.get("data") or {})
            codes = data.get("coduri_invitat", {})
            if not isinstance(codes, dict):
                continue
            for code_type, role in (("spectator", "vizitator"), ("editor", "editor")):
                existing = normalize_access_code(codes.get(code_type, ""))
                if existing and hmac.compare_digest(existing, normalized):
                    return {"path": path, "owner": owner, "role": role,
                            "code_type": code_type, "code": codes[code_type], "data": data,
                            "access_method": "cod"}
        return None
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    for folder in BASE_DIR.iterdir():
        if not folder.is_dir() or folder.name.startswith("_"):
            continue
        for path in folder.glob("*.json"):
            try:
                data = load_league(path)
            except ValueError:
                continue
            codes = data.get("coduri_invitat", {})
            if not isinstance(codes, dict):
                continue
            for code_type, role in (("spectator", "vizitator"), ("editor", "editor")):
                existing = normalize_access_code(codes.get(code_type, ""))
                if existing and hmac.compare_digest(existing, normalized):
                    return {"path": path, "owner": folder.name, "role": role,
                            "code_type": code_type, "code": codes[code_type], "data": data,
                            "access_method": "cod"}
    return None


def save_guest_selection(path, invitation, team, player):
    fresh = load_league(path)
    active = next((item for item in fresh.get("invitatii", [])
                   if item.get("id") == invitation.get("id")
                   and hmac.compare_digest(str(item.get("token", "")), str(invitation.get("token", "")))
                   and item.get("activ", True)), None)
    if not active:
        raise ValueError("Invitația a fost revocată.")
    if team not in fresh.get("echipe", {}) or player not in fresh["echipe"][team].get("jucatori", {}):
        raise ValueError("Alege un jucător care există în lot.")
    fresh.setdefault("selectii_membri", {})[invitation["id"]] = {
        "nume": invitation.get("nume", "Invitat"), "tip": invitation.get("tip", "spectator"),
        "echipa": team, "jucator": player, "actualizat": dt.datetime.now().timestamp()}
    _store_league(path, fresh)


def join_league_with_code(entry, username, access_code, member_choice=None):
    fresh = load_league(entry["path"])
    codes = fresh.get("coduri_invitat", {})
    if not isinstance(codes, dict):
        codes = {}
    code_type = entry["code_type"]
    active_code = normalize_access_code(codes.get(code_type, ""))
    if not active_code or not hmac.compare_digest(active_code, normalize_access_code(access_code)):
        raise ValueError("Codul a fost schimbat. Cere proprietarului codul nou.")
    role = "editor" if code_type == "editor" else "vizitator"
    choice = member_choice if code_type == "spectator" else None
    member_type = "jucator" if choice and choice.get("kind") == "jucator" else "spectator"
    users_to_save = None
    if entry["owner"].casefold() != username.casefold():
        fresh.setdefault("membri", [])
        membership = next((item for item in fresh["membri"]
                           if str(item.get("username", "")).casefold() == username.casefold()), None)
        values = {"username": username, "rol": role, "tip": member_type, "activ": True,
                  "creat": dt.datetime.now().strftime("%d.%m.%Y %H:%M"), "sursa": "cod"}
        if membership is None:
            fresh["membri"].append(values)
        else:
            membership.update(values)
        if choice and choice.get("kind") == "jucator":
            team, player = choice.get("team"), choice.get("player")
            if team not in fresh.get("echipe", {}) or player not in fresh["echipe"][team].get("jucatori", {}):
                raise ValueError("Jucătorul ales nu mai există în lot. Alege din nou.")
            selection = {"echipa": team, "jucator": player, "tip": "jucator",
                         "actualizat": dt.datetime.now().timestamp()}
            fresh.setdefault("selectii_membri", {})[username] = selection
            users = load_users()
            if username in users:
                users[username].setdefault("selectii_ligi", {})[league_key(entry)] = {
                    **selection, "pozitie": users[username].get("pozitie", "")}
                users_to_save = users
        _store_league(entry["path"], fresh)
        # Save the league membership/selection first. If account-profile
        # synchronization fails, the player can still enter and the choice
        # remains available from the league data.
        if users_to_save is not None:
            try:
                save_users(users_to_save)
                st.session_state.pop("player_profile_sync_error", None)
            except Exception as exc:
                st.session_state["player_profile_sync_error"] = str(exc)
    return role if entry["owner"].casefold() != username.casefold() else "owner"


def save_code_member_choice(entry, username, team=None, player=None):
    """Persist player/spectator choice for a logged-in viewer after entering the league."""
    fresh = load_league(entry["path"])
    member = next((item for item in fresh.setdefault("membri", [])
                   if str(item.get("username", "")).casefold() == username.casefold()), None)
    if member is None:
        member = {"username": username, "rol": "vizitator", "activ": True,
                  "creat": dt.datetime.now().strftime("%d.%m.%Y %H:%M"), "sursa": "cod"}
        fresh["membri"].append(member)
    if player:
        if team not in fresh.get("echipe", {}) or player not in fresh["echipe"][team].get("jucatori", {}):
            raise ValueError("Jucătorul ales nu mai există în lot. Alege din nou.")
        member["tip"] = "jucator"
        selection = {"echipa": team, "jucator": player, "tip": "jucator",
                     "actualizat": dt.datetime.now().timestamp()}
        fresh.setdefault("selectii_membri", {})[username] = selection
    else:
        member["tip"] = "spectator"
        fresh.setdefault("selectii_membri", {}).pop(username, None)
        selection = None
    _store_league(entry["path"], fresh)

    users = load_users()
    record = users.get(username)
    if record is not None:
        selections = record.setdefault("selectii_ligi", {})
        if selection:
            selections[league_key(entry)] = {**selection, "pozitie": record.get("pozitie", "")}
        else:
            selections.pop(league_key(entry), None)
        try:
            save_users(users)
            st.session_state.pop("player_profile_sync_error", None)
        except Exception as exc:
            st.session_state["player_profile_sync_error"] = str(exc)


def create_user_league(username, name, source_entry=None, league_type="Ligă"):
    if SUPABASE_ENABLED:
        path = db_league_path(username, uuid.uuid4())
        copied_teams = {}
        if source_entry:
            source_data = load_league(source_entry["path"])
            copied_teams = {
                team: {"jucatori": {player: dict(STATS_JUCATOR) for player in info.get("jucatori", {})},
                       **STATS_ECHIPA}
                for team, info in source_data.get("echipe", {}).items()
            }
        created_data = {"nume_liga": name.strip() or "Liga mea", "echipe": copied_teams,
                        "istoric_meciuri": [], "program": [], "transferuri": [], "cupe": [], "membri": [],
                        "coduri_invitat": new_league_access_codes()}
        if league_type in ("Ligă + cupă", "Cupă"):
            cup = make_cup(list(copied_teams), f"Cupa {created_data['nume_liga']}") if len(copied_teams) >= 2 else {
                "id": uuid.uuid4().hex[:8], "nume": f"Cupa {created_data['nume_liga']}", "runde": [],
                "status": "în desfășurare", "castigatoare": None}
            created_data["cupe"].append(cup)
        save_league(path, created_data)
        saved_data = load_league(path)
        if saved_data.get("nume_liga") != created_data["nume_liga"]:
            raise ValueError("Liga nu a putut fi confirmată în Supabase după salvare. Verifică dacă acest cont există în app_users și dacă secretul SUPABASE_SERVICE_ROLE_KEY este corect.")
        return path
    user_folder = BASE_DIR / username
    user_folder.mkdir(parents=True, exist_ok=True)
    path = user_folder / f"{safe_slug(name)}.json"
    suffix = 2
    while path.exists():
        path = user_folder / f"{safe_slug(name)}-{suffix}.json"
        suffix += 1
    copied_teams = {}
    if source_entry:
        source_data = load_league(source_entry["path"])
        copied_teams = {
            team: {"jucatori": {player: dict(STATS_JUCATOR) for player in info.get("jucatori", {})},
                   **STATS_ECHIPA}
            for team, info in source_data.get("echipe", {}).items()
        }
    created_data = {"nume_liga": name.strip() or "Liga mea", "echipe": copied_teams,
                    "istoric_meciuri": [], "program": [], "transferuri": [], "cupe": [], "membri": [],
                    "coduri_invitat": new_league_access_codes()}
    if league_type in ("Ligă + cupă", "Cupă"):
        cup = make_cup(list(copied_teams), f"Cupa {created_data['nume_liga']}") if len(copied_teams) >= 2 else {
            "id": uuid.uuid4().hex[:8], "nume": f"Cupa {created_data['nume_liga']}", "runde": [],
            "status": "în desfășurare", "castigatoare": None}
        created_data["cupe"].append(cup)
    save_league(path, created_data)
    saved_data = load_league(path)
    if saved_data.get("nume_liga") != created_data["nume_liga"]:
        raise ValueError("Liga nu a putut fi confirmată după salvare.")
    return path


def delete_user_league(username, entry):
    """Delete one league only when the current account owns it."""
    path = Path(entry["path"])
    if entry.get("role") != "owner" or str(entry.get("owner", "")).casefold() != username.casefold():
        raise ValueError("Poți șterge doar o ligă care îți aparține.")
    key = league_key(entry)
    if is_db_league_path(path):
        table = supabase_client().table("app_leagues")
        owned_row = (table.select("id").eq("id", db_league_id(path))
                     .eq("owner_username", username).limit(1).execute().data or [])
        if not owned_row:
            raise ValueError("Liga nu a fost găsită în Supabase sau nu îți aparține.")
        table.delete().eq("id", db_league_id(path)).eq("owner_username", username).execute()
        remaining = (table.select("id").eq("id", db_league_id(path))
                     .eq("owner_username", username).limit(1).execute().data or [])
        if remaining:
            raise ValueError("Supabase nu a confirmat ștergerea ligii.")
    else:
        data_root = BASE_DIR.resolve()
        resolved_path = path.resolve()
        if resolved_path.parent.parent != data_root or resolved_path.parent.name.casefold() != username.casefold():
            raise ValueError("Locația ligii nu corespunde contului tău.")
        if not resolved_path.is_file():
            raise ValueError("Fișierul ligii nu mai există.")
        resolved_path.unlink()
        backup = resolved_path.with_suffix(resolved_path.suffix + ".bak")
        if backup.is_file():
            backup.unlink()
    users = load_users()
    record = users.get(username.casefold())
    if record:
        selections = record.get("selectii_ligi")
        if not isinstance(selections, dict):
            selections = record["selectii_ligi"] = {}
        selections.pop(key, None)
        if record.get("liga_preferata") == key:
            record.pop("liga_preferata", None)
        try:
            save_users(users)
        except Exception:
            pass
    return key


def load_league(path):
    if is_db_league_path(path):
        try:
            result = (supabase_client().table("app_leagues").select("data")
                      .eq("id", db_league_id(path)).limit(1).execute().data or [])
            if not result:
                raise ValueError("Liga nu mai există în baza de date.")
            return normalizeaza_date(result[0].get("data") or {})
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Nu pot citi liga din Supabase: {exc}") from exc
    try:
        with path.open("r", encoding="utf-8") as handle:
            return normalizeaza_date(json.load(handle))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Nu pot citi fișierul ligii: {exc}") from exc


def _store_league(path, data):
    if is_db_league_path(path):
        payload = normalizeaza_date(data)
        supabase_client().table("app_leagues").upsert({
            "id": db_league_id(path), "owner_username": path.parent.name,
            "nume": payload.get("nume_liga", "Liga mea"), "data": payload,
            "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }, on_conflict="id").execute()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(normalizeaza_date(data), handle, ensure_ascii=False, indent=2)
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    os.replace(temp, path)


def save_league(path, data):
    role = st.session_state.get("active_league_role")
    if role not in {"owner", "editor"}:
        st.error("Ai acces doar pentru vizualizare în această ligă.")
        st.stop()
    exists = path.exists()
    if is_db_league_path(path):
        exists = bool(supabase_client().table("app_leagues").select("id")
                      .eq("id", db_league_id(path)).limit(1).execute().data)
    if role == "editor" and exists:
        current = load_league(path)
        access = st.session_state.get("active_guest_access")
        if access and Path(access.get("path", "")) == path:
            current_codes = current.get("coduri_invitat", {})
            if not isinstance(current_codes, dict):
                current_codes = {}
            current_code = normalize_access_code(
                current_codes.get("editor", ""))
            if not current_code or not hmac.compare_digest(
                    current_code, normalize_access_code(access.get("code", ""))):
                st.error("Codul de editor a fost schimbat sau revocat.")
                st.stop()
        guest = st.session_state.get("active_guest_invite")
        if guest and Path(guest.get("path", "")) == path:
            active_invite = next((invite for invite in current.get("invitatii", [])
                if hmac.compare_digest(str(invite.get("token", "")), str(guest.get("token", "")))
                and invite.get("activ", True)), None)
            if not active_invite or active_invite.get("tip") == "spectator" or active_invite.get("rol") != "editor":
                st.error("Invitația nu mai permite modificarea ligii.")
                st.stop()
        # Editors can change league content but cannot grant themselves or others access.
        data["membri"] = current.get("membri", [])
        for key in ("invitatii", "selectii_membri", "coduri_invitat", "partajare", "partajare_adresa", "partajare_setari"):
            if key in current:
                data[key] = current[key]
    _store_league(path, data)


def build_match(home, away, events, round_no=None, walkover=None, reason=""):
    if walkover:
        goals_home, goals_away = (3, 0) if walkover == home else (0, 3)
        events = []
    else:
        goals_home = goals_away = 0
        for event in events:
            if event["tip"] in TIPURI_GOL:
                if event["echipa"] == home:
                    goals_home += 1
                else:
                    goals_away += 1
            elif event["tip"] == "Autogol":
                if event["echipa"] == home:
                    goals_away += 1
                else:
                    goals_home += 1
    stats = {}
    for event in events:
        team_stats = stats.setdefault(event["echipa"], {})
        if event.get("tip") == "Schimbare":
            continue
        player_stats = team_stats.setdefault(event["jucator"], dict(STATS_JUCATOR))
        if event["tip"] in TIPURI_GOL:
            player_stats["goluri"] += 1
            if event.get("asist"):
                team_stats.setdefault(event["asist"], dict(STATS_JUCATOR))["asisturi"] += 1
        elif event["tip"] == "Cartonaș Galben":
            player_stats["cartonase_galbene"] += 1
        elif event["tip"] == "Cartonaș Roșu":
            player_stats["cartonase_rosii"] += 1
    match = {"id": uuid.uuid4().hex[:8], "etapa": round_no,
             "modificat": int(dt.datetime.now().timestamp() * 1000),
             "e1": home, "e2": away, "goluri_e1": goals_home, "goluri_e2": goals_away,
             "mod_e1": stats.get(home, {}), "mod_e2": stats.get(away, {}),
             "evenimente": sorted(events, key=lambda e: e["minut"])}
    if walkover:
        match.update(masa_verde=walkover, motiv_mv=reason)
    return match


def match_substitution_summary(match):
    substitutions = [event for event in match.get("evenimente", [])
                     if event.get("tip") == "Schimbare"]
    return " · ".join(f"{event.get('echipa')}: {event.get('jucator')} → {event.get('intra')}"
                      for event in substitutions) or "–"


def render_match_player_contributions(match):
    labels = {
        "goluri": "goluri", "asisturi": "assisturi", "cartonase_galbene": "cartonașe galbene",
        "cartonase_rosii": "cartonașe roșii", "penaltyuri_ratate": "penalty-uri ratate",
        "autogoluri": "autogoluri", "schimbari": "schimbări",
    }
    contributions = {}

    def add(player, stat):
        if not player:
            return
        contributions.setdefault(str(player), {}).setdefault(stat, 0)
        contributions[str(player)][stat] += 1

    events = match.get("evenimente", [])
    if events:
        for event in events:
            kind = event.get("tip")
            player = event.get("jucator")
            if kind in TIPURI_GOL:
                add(player, "goluri")
            elif kind == "Autogol":
                add(player, "autogoluri")
            elif kind == "Penalty Ratat":
                add(player, "penaltyuri_ratate")
            elif kind == "Cartonaș Galben":
                add(player, "cartonase_galbene")
            elif kind == "Cartonaș Roșu":
                add(player, "cartonase_rosii")
            elif kind == "Schimbare":
                add(player, "schimbari")
                add(event.get("intra"), "schimbari")
            add(event.get("asist"), "asisturi")
    else:
        for team_key in ("mod_e1", "mod_e2"):
            for player, stats in match.get(team_key, {}).items():
                for field in ("goluri", "asisturi", "cartonase_galbene", "cartonase_rosii"):
                    amount = int(stats.get(field, 0) or 0)
                    if amount:
                        contributions.setdefault(player, {})[field] = amount
    if contributions:
        st.markdown("**Contribuțiile jucătorilor**")
        for player, stats in contributions.items():
            summary = [f"{amount} {labels[field]}" for field, amount in stats.items() if amount]
            if summary:
                st.write(f"{player} — " + ", ".join(summary))
    return bool(contributions)


def render_match_history_details(match):
    st.markdown(f"**{match.get('e1')} {match.get('goluri_e1', 0)}–{match.get('goluri_e2', 0)} {match.get('e2')}**")
    if match.get("masa_verde"):
        st.caption(f"Victorie la masa verde pentru {match.get('masa_verde')}"
                   + (f" · {match.get('motiv_mv')}" if match.get("motiv_mv") else ""))
    events = sorted(match.get("evenimente", []),
                    key=lambda event: int(event.get("minut", 0) or 0))
    if events:
        for event in events:
            minute = event.get("afișaj_minut") or f"{event.get('minut', '—')}′"
            team = event.get("echipa", "")
            if event.get("tip") == "Schimbare":
                st.write(f"{minute} · {team} · Schimbare: {event.get('jucator', '—')} → {event.get('intra', '—')}")
            else:
                detail = f"{minute} · {team} · {event.get('tip', 'Eveniment')} · {event.get('jucator', '—')}"
                if event.get("asist"):
                    detail += f" (assist: {event['asist']})"
                st.write(detail)
        render_match_player_contributions(match)
        return
    if not render_match_player_contributions(match):
        st.caption("Meciul a fost salvat fără evenimente individuale.")


def render_match_event_entry(data, home, away, draft_id, initial_events=None,
                             minute_min=1, minute_max=150, substitution_history=None):
    """Interactive event entry with a live score preview."""
    state_key = f"match_draft_{draft_id}"
    events = st.session_state.setdefault(state_key, copy.deepcopy(initial_events or []))
    next_key = f"{state_key}_next"
    entry_id = st.session_state.get(next_key, 0)
    st.markdown("#### Evenimentele meciului")
    st.caption("Adaugă goluri, cartonașe și schimbări. Scorul se actualizează automat; schimbările nu modifică statisticile de goluri.")
    left, right = st.columns([1, 1])
    with left:
        minute = st.number_input("Minut", min_value=minute_min, max_value=minute_max, value=minute_min,
                                 step=1, key=f"{state_key}_minute_{entry_id}")
        event_team = st.selectbox("Echipa", [home, away], key=f"{state_key}_team_{entry_id}")
        event_type = st.selectbox("Eveniment", TIPURI_EVENIMENT, key=f"{state_key}_type_{entry_id}")
    roster = list(data.get("echipe", {}).get(event_team, {}).get("jucatori", {}))
    team_token = hashlib.sha1(event_team.encode()).hexdigest()[:6]
    rule = data.get("setari_liga", {}).get("substitution_rule", "5_no_return")
    substitution_limit = 5 if rule.startswith("5_") else None
    allow_reentry = rule in {"5_return", "unlimited_return"}
    all_match_events = [*(substitution_history or []), *events]
    team_subs = [event for event in all_match_events
                 if event.get("tip") == "Schimbare" and event.get("echipa") == event_team]
    team_sub_count = len(team_subs)
    limit_reached = substitution_limit is not None and team_sub_count >= substitution_limit
    player_name = ""
    incoming_player = None
    assist = None
    if event_type == "Schimbare":
        if limit_reached:
            st.info("Echipa a folosit deja toate cele cinci schimbări permise în acest meci.")
        elif len(roster) < 2:
            st.info("Adaugă cel puțin doi jucători în lotul echipei pentru a înregistra o schimbare.")
        else:
            already_out = {event.get("jucator") for event in team_subs if event.get("jucator")}
            outgoing_options = [player for player in roster if allow_reentry or player not in already_out]
            if not outgoing_options:
                st.info("Nu mai sunt jucători eligibili pentru a ieși; cei schimbați nu pot reintra.")
            else:
                player_name = st.selectbox("Jucător care iese", outgoing_options,
                    key=f"{state_key}_out_{team_token}_{entry_id}")
                incoming_options = [player for player in roster if player != player_name
                    and (allow_reentry or player not in already_out)]
                if incoming_options:
                    incoming_player = st.selectbox("Jucător care intră", incoming_options,
                        key=f"{state_key}_in_{team_token}_{entry_id}")
                else:
                    st.info("Nu există un alt jucător eligibil care să intre.")
    else:
        player_options = [*roster, "Alt jucător…"]
        player_choice = st.selectbox("Jucător", player_options,
            key=f"{state_key}_player_{team_token}_{entry_id}")
        player_name = (st.text_input("Numele jucătorului", key=f"{state_key}_player_manual_{team_token}_{entry_id}")
                       if player_choice == "Alt jucător…" else player_choice)
        if event_type in TIPURI_GOL:
            assist_options = ["Fără assist", *roster, "Alt jucător…"]
            assist_choice = st.selectbox("Assist (opțional)", assist_options,
                                         key=f"{state_key}_assist_{team_token}_{entry_id}")
            if assist_choice == "Alt jucător…":
                assist = st.text_input("Numele celui care a dat assist", key=f"{state_key}_assist_manual_{team_token}_{entry_id}").strip() or None
            elif assist_choice != "Fără assist":
                assist = assist_choice
    disabled_add = event_type == "Schimbare" and (
        limit_reached or len(roster) < 2 or not player_name or not incoming_player)
    if st.button("＋ Adaugă eveniment", type="primary", disabled=disabled_add,
                 key=f"{state_key}_add_{entry_id}"):
        player_name = player_name.strip()
        if event_type == "Schimbare":
            if not player_name or not incoming_player or player_name == incoming_player:
                st.error("Alege jucătorii care ies și intră.")
            elif not allow_reentry and player_name in already_out:
                st.error("Jucătorul a ieșit deja și nu mai poate fi schimbat din nou în acest meci.")
            elif not allow_reentry and incoming_player in already_out:
                st.error("Jucătorul care a ieșit mai devreme nu mai poate reintra.")
            elif substitution_limit is not None and len(team_subs) >= substitution_limit:
                st.error("Echipa a folosit deja toate cele cinci schimbări permise.")
            else:
                events.append({"echipa": event_team, "minut": int(minute), "tip": event_type,
                               "jucator": player_name, "intra": incoming_player})
                st.session_state[next_key] = st.session_state.get(next_key, 0) + 1
                st.rerun()
        elif not player_name:
            st.error("Alege sau scrie numele jucătorului.")
        elif assist and assist.casefold() == player_name.casefold():
            st.error("Marcatorul nu poate să-și dea assist lui însuși.")
        else:
            events.append({"echipa": event_team, "minut": int(minute), "tip": event_type,
                           "jucator": player_name, "asist": assist})
            st.session_state[next_key] = st.session_state.get(next_key, 0) + 1
            st.rerun()
    preview = build_match(home, away, events)
    st.markdown(f"### {home}  **{preview['goluri_e1']} – {preview['goluri_e2']}**  {away}")
    if events:
        st.markdown("**Evenimente adăugate**")
        for index, event in enumerate(list(events)):
            if event.get("tip") == "Schimbare":
                detail = f"{event['minut']}′ · {event['echipa']} · Schimbare: {event.get('jucator')}  →  {event.get('intra', '—')}"
            else:
                detail = f"{event['minut']}′ · {event['echipa']} · {event['tip']} · {event['jucator']}"
            if event.get("asist"):
                detail += f" (assist: {event['asist']})"
            c1, c2 = st.columns([8, 1])
            c1.write(detail)
            if c2.button("Șterge", key=f"{state_key}_delete_{index}"):
                events.pop(index)
                st.rerun()
    else:
        st.caption("Nu ai adăugat încă evenimente. Poți salva scorul 0–0.")
    return events


def render_knockout_result_entry(data, home, away, draft_id, tie_resolution,
                                 aggregate_before=(0, 0), decide=True,
                                 button_label="Salvează rezultatul", button_key=None):
    """Collect regulation and optional extra-time events, then resolve the tie."""
    st.caption("Introdu golurile din minutele regulamentare (1–90).")
    regular_events = render_match_event_entry(data, home, away, draft_id,
                                               minute_min=1, minute_max=90)
    regular_match = build_match(home, away, regular_events)
    regular_home_total = aggregate_before[0] + regular_match["goluri_e1"]
    regular_away_total = aggregate_before[1] + regular_match["goluri_e2"]
    regular_tied = regular_home_total == regular_away_total
    if aggregate_before != (0, 0):
        st.markdown(f"**Scor agregat după 90′:** {home} {regular_home_total} – {regular_away_total} {away}")
    extra_events = []
    if decide and regular_tied and tie_resolution == "extra_time":
        st.info("Egalitate după minutele regulamentare. Se joacă două reprize de prelungiri (minutele 91–120).")
        extra_events = render_match_event_entry(data, home, away, f"{draft_id}_extra",
                                                 minute_min=91, minute_max=120,
                                                 substitution_history=regular_events)
    final_events = [*regular_events, *extra_events]
    final_match = build_match(home, away, final_events)
    final_home_total = aggregate_before[0] + final_match["goluri_e1"]
    final_away_total = aggregate_before[1] + final_match["goluri_e2"]
    if decide and regular_tied:
        if tie_resolution == "extra_time":
            score_label = "Scor după prelungiri/agregat"
        elif aggregate_before != (0, 0):
            score_label = "Scor agregat înainte de penaltyuri"
        else:
            score_label = "Scor după minutele regulamentare"
        st.markdown(f"**{score_label}:** {final_home_total} – {final_away_total}")
        needs_penalties = final_home_total == final_away_total
    else:
        needs_penalties = False
    penalty_winner = None
    if needs_penalties:
        st.caption("Egalitate în continuare. Alege echipa care se califică după penaltyuri.")
        penalty_winner = st.selectbox("Câștigătoare la penaltyuri", [home, away],
                                      key=f"{draft_id}_penalty_winner")
    submitted = st.button(button_label, type="primary", key=button_key or f"{draft_id}_save")
    if not submitted:
        return None, None, False, False
    if not decide:
        return final_match, None, False, True
    if needs_penalties:
        winner = penalty_winner
    else:
        winner = home if final_home_total > final_away_total else away
    return final_match, winner, needs_penalties, True


def round_title(match_count):
    return {1: "Finala", 2: "Semifinale", 4: "Sferturi", 8: "Optimi",
            16: "Șaisprezecimi"}.get(match_count, f"Runda cu {match_count} meciuri")


def make_cup(teams, name, tur_retur=False):
    shuffled = list(teams)
    import random
    random.shuffle(shuffled)
    bracket_size = 1
    while bracket_size < len(shuffled):
        bracket_size *= 2
    byes = bracket_size - len(shuffled)
    rounds, matches_count = [], bracket_size // 2
    while matches_count:
        rounds.append({"nume": round_title(matches_count), "meciuri": [
            {"id": uuid.uuid4().hex[:8], "e1": None, "e2": None,
             "meci": None, "castigator": None, "penalti": False}
            for _ in range(matches_count)]})
        matches_count //= 2
    cursor = 0
    for index, slot in enumerate(rounds[0]["meciuri"]):
        if index < byes:
            slot["e1"] = shuffled[cursor]
            cursor += 1
        else:
            slot["e1"], slot["e2"] = shuffled[cursor:cursor + 2]
            cursor += 2
    cup = {"id": uuid.uuid4().hex[:8], "nume": name, "echipe": list(teams),
           "tur_retur": bool(tur_retur),
           "creata": dt.date.today().strftime("%d.%m.%Y"), "runde": rounds,
           "status": "în desfășurare", "castigatoare": None}
    propagate_cup_byes(cup)
    return cup


def advance_cup_winner(cup, round_index, match_index):
    slot = cup["runde"][round_index]["meciuri"][match_index]
    if round_index + 1 == len(cup["runde"]):
        cup["castigatoare"] = slot["castigator"]
        cup["status"] = "terminată"
    else:
        next_slot = cup["runde"][round_index + 1]["meciuri"][match_index // 2]
        next_slot["e1" if match_index % 2 == 0 else "e2"] = slot["castigator"]


def participanti_supercupa(data, cup):
    cup_winner = cup.get("castigatoare")
    if not cup_winner:
        return None, None, "Cupa selectată nu are încă o câștigătoare."
    table = ranking(data)
    teams = [row["Echipă"] for row in table]
    if len(teams) < 2:
        return None, None, "Ai nevoie de cel puțin două echipe în clasament."
    champion = teams[0]
    return (cup_winner, champion, "campioana ligii") if cup_winner != champion else (
        cup_winner, teams[1], "locul 2 din ligă (dubla ligă + cupă)")


def make_supercup(name, team_a, team_b, source_cup_id=None, tur_retur=False):
    return {"id": uuid.uuid4().hex[:8], "nume": name, "super": True,
            "tur_retur": bool(tur_retur),
            "sursa_cupa": source_cup_id, "echipe": [team_a, team_b],
            "creata": dt.date.today().strftime("%d.%m.%Y"),
            "runde": [{"nume": "Finala", "meciuri": [{"id": uuid.uuid4().hex[:8],
                "e1": team_a, "e2": team_b, "meci": None,
                "castigator": None, "penalti": False}]}],
            "status": "în desfășurare", "castigatoare": None}


def definitii_premii(data):
    league_name = data.get("nume_liga") or "Liga"
    awards = [{"cheie": "campioana", "titlu": "🏆 Campioana ligii", "tip": "echipa",
               "trofeu": f"Campioană — {league_name}"}]
    for cup in data.get("cupe", []):
        awards.append({"cheie": f"cupa:{cup.get('id')}",
            "titlu": f"🏅 Câștigătoarea Supercupei — {cup.get('nume', 'Cupa')}" if cup.get("super")
                     else f"🏆 Câștigătoarea — {cup.get('nume', 'Cupa')}",
            "tip": "echipa", "trofeu": (f"Trofeul Supercupei — {cup.get('nume', 'Supercupa')}"
                if cup.get("super") else f"Câștigătoare {cup.get('nume', 'Cupa')}")})
    awards.append({"cheie": "gheata_liga", "titlu": "👟 Gheata de Aur — Ligă", "tip": "jucator", "trofeu": "Gheata de Aur — Ligă"})
    if any(not cup.get("super") for cup in data.get("cupe", [])):
        awards.append({"cheie": "gheata_cupa", "titlu": "👟 Gheata de Aur — Cupă", "tip": "jucator", "trofeu": "Gheata de Aur — Cupă"})
    awards.extend([
        {"cheie": "balon", "titlu": "🌟 Balonul de Aur", "tip": "jucator", "trofeu": "Balonul de Aur"},
        {"cheie": "yashin", "titlu": "🧤 Trofeul Yashin · portar", "tip": "jucator", "trofeu": "Trofeul Yashin", "poz": "port"},
        {"cheie": "kopa", "titlu": "⭐ Trofeul Kopa · tânăr", "tip": "jucator", "trofeu": "Trofeul Kopa"},
        {"cheie": "fundas", "titlu": "🛡 Cel mai bun fundaș", "tip": "jucator", "trofeu": "Cel mai bun fundaș", "poz": "fund"},
        {"cheie": "mijlocas", "titlu": "🧠 Cel mai bun mijlocaș", "tip": "jucator", "trofeu": "Cel mai bun mijlocaș", "poz": "mijloc"},
        {"cheie": "atacant", "titlu": "⚽ Cel mai bun atacant", "tip": "jucator", "trofeu": "Cel mai bun atacant", "poz": "atac"},
    ])
    return awards


def award_is_automatic(award):
    return award.get("cheie") in {"campioana", "gheata_liga", "gheata_cupa"} or str(
        award.get("cheie", "")).startswith("cupa:")


def event_totals(matches):
    result = {}
    for played_match in matches:
        for event in played_match.get("evenimente", []):
            player_name = event.get("jucator")
            if not player_name or event.get("tip") not in TIPURI_GOL:
                continue
            key = (event.get("echipa") or "", player_name)
            totals = result.setdefault(key, {"goluri": 0, "asisturi": 0})
            totals["goluri"] += 1
            assist_name = event.get("asist")
            if assist_name:
                result.setdefault((key[0], assist_name), {"goluri": 0, "asisturi": 0})["asisturi"] += 1
    return result


def final_player_identity(data, team, player):
    visited = {team}
    while True:
        transfer = next((item for item in reversed(data.get("transferuri", []))
                         if item.get("de_la") == team
                         and str(item.get("jucator", "")).casefold() == player.casefold()), None)
        if not transfer or transfer.get("la") in visited:
            return team, player
        team, player = transfer["la"], transfer.get("nume_nou", player)
        visited.add(team)


def automatic_award_winners(data, award):
    key = award.get("cheie", "")
    if key == "campioana":
        table = ranking(data)
        return [(table[0]["Echipă"], "")] if table else []
    if key.startswith("cupa:"):
        cup_id = key.split(":", 1)[1]
        cup = next((item for item in data.get("cupe", []) if str(item.get("id")) == cup_id), None)
        winner = cup.get("castigatoare") if cup else None
        return [(winner, "")] if winner else []
    if key in ("gheata_liga", "gheata_cupa"):
        if key == "gheata_liga":
            matches = data.get("istoric_meciuri", [])
        else:
            matches = [match for cup in data.get("cupe", []) if not cup.get("super")
                for round_data in cup.get("runde", []) for slot in round_data.get("meciuri", [])
                for match in (slot.get("meci"), slot.get("meci_retur")) if match]
        raw_totals = event_totals(matches)
        totals = {}
        for (team, player), stats in raw_totals.items():
            identity = final_player_identity(data, team, player)
            if identity[0] in data.get("echipe", {}) and identity[1] in data["echipe"][identity[0]].get("jucatori", {}):
                totals[identity] = totals.get(identity, 0) + stats["goluri"]
        best = max(totals.values(), default=0)
        return sorted(candidate for candidate, goals in totals.items() if best > 0 and goals == best)
    return []


def award_winners(data, award):
    if award_is_automatic(award):
        return automatic_award_winners(data, award)
    selected = data.get("premii_alese", {}).get(award["cheie"], {})
    if award["tip"] == "echipa":
        return [(selected.get("echipa"), "")] if selected.get("echipa") else []
    return [(selected.get("echipa"), selected.get("jucator"))] if selected.get("echipa") and selected.get("jucator") else []


def award_candidates(data, award):
    candidates = [(team, player) for team, info in data.get("echipe", {}).items()
                  for player in info.get("jucatori", {})]
    target_position = award.get("poz")
    if target_position:
        candidates.sort(key=lambda choice: (
            0 if target_position in str(data["echipe"].get(choice[0], {}).get("jucatori", {})
                                        .get(choice[1], {}).get("pozitie", "")).casefold() else 1,
            choice[1].casefold(), choice[0].casefold()))
    else:
        candidates.sort(key=lambda choice: (choice[1].casefold(), choice[0].casefold()))
    return candidates


def award_voter_id(username=None, guest_invite=None):
    if username:
        identity = f"user:{username.casefold()}"
    elif guest_invite:
        invitation = guest_invite.get("invitation", {})
        identity = f"invite:{invitation.get('id')}"
    else:
        return None
    return "award-voter:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()


def award_vote_scores(data, award_key):
    scores = {}
    all_ballots = data.get("voturi_premii", {})
    if not isinstance(all_ballots, dict):
        return scores
    ballots = all_ballots.get(award_key, {})
    if not isinstance(ballots, dict):
        return scores
    award = next((item for item in definitii_premii(data)
                  if item["cheie"] == award_key and item["tip"] == "jucator"), None)
    valid_candidates = set(award_candidates(data, award)) if award else set()
    for ballot in ballots.values():
        choices = ballot.get("alegeri", []) if isinstance(ballot, dict) else ballot
        if not isinstance(choices, list):
            continue
        for place, choice in enumerate(choices[:5]):
            if isinstance(choice, dict):
                candidate = (choice.get("echipa"), choice.get("jucator"))
            elif isinstance(choice, (list, tuple)) and len(choice) == 2:
                candidate = tuple(choice)
            else:
                continue
            if candidate in valid_candidates:
                scores[candidate] = scores.get(candidate, 0) + (5 - place)
    return scores


def finalize_award_vote_results(data):
    awards = [award for award in definitii_premii(data)
              if award["tip"] == "jucator" and not award_is_automatic(award)]
    selected = data.setdefault("premii_alese", {})
    for award in awards:
        scores = award_vote_scores(data, award["cheie"])
        best = max(scores.values(), default=0)
        winners = [candidate for candidate, points in scores.items() if points == best and best > 0]
        if len(winners) == 1:
            team, player = winners[0]
            selected[award["cheie"]] = {"echipa": team, "jucator": player,
                "puncte_vot": best, "modificat": int(dt.datetime.now().timestamp() * 1000)}
        else:
            selected.pop(award["cheie"], None)


def save_award_ballot(path, award_key, choices, username=None, guest_invite=None):
    fresh = load_league(path)
    settings = fresh.get("setari_liga", {})
    if settings.get("award_voting_mode", "direct") != "vote" or not settings.get("award_voting_open"):
        raise ValueError("Votul pentru premii nu este deschis.")
    award = next((item for item in definitii_premii(fresh)
                  if item["cheie"] == award_key and item["tip"] == "jucator"
                  and not award_is_automatic(item)), None)
    if not award:
        raise ValueError("Premiul selectat nu mai există.")
    voter_id = award_voter_id(username, guest_invite)
    if not voter_id:
        raise ValueError("Intră în ligă cu un cont sau o invitație pentru a vota.")
    if username:
        owner = Path(path).parent.name.casefold()
        member = next((item for item in fresh.get("membri", [])
            if str(item.get("username", "")).casefold() == username.casefold()
            and item.get("activ", True)), None)
        if owner != username.casefold() and not member:
            raise ValueError("Nu mai ai acces la această ligă.")
    else:
        invitation = guest_invite.get("invitation", {})
        active = next((item for item in fresh.get("invitatii", [])
            if item.get("id") == invitation.get("id")
            and hmac.compare_digest(str(item.get("token", "")), str(invitation.get("token", "")))
            and item.get("activ", True)), None)
        if not active:
            raise ValueError("Invitația nu mai este activă.")
    candidates = set(award_candidates(fresh, award))
    normalized = [tuple(choice) for choice in choices]
    if len(normalized) != 5 or len(set(normalized)) != 5:
        raise ValueError("Alege exact cinci jucători diferiți, în ordinea preferinței.")
    if any(choice not in candidates for choice in normalized):
        raise ValueError("Unul dintre jucătorii aleși nu mai este eligibil pentru acest premiu.")
    all_ballots = fresh.get("voturi_premii")
    if not isinstance(all_ballots, dict):
        all_ballots = fresh["voturi_premii"] = {}
    award_ballots = all_ballots.get(award_key)
    if not isinstance(award_ballots, dict):
        award_ballots = all_ballots[award_key] = {}
    award_ballots[voter_id] = {
        "alegeri": [{"echipa": team, "jucator": player} for team, player in normalized],
        "trimis": int(dt.datetime.now().timestamp() * 1000)}
    _store_league(path, fresh)


def render_award_ballot(data, award, path, username=None, guest_invite=None, widget_key="",
                        touch_friendly=False):
    if award.get("tip") != "jucator" or award_is_automatic(award):
        return
    settings = data.get("setari_liga", {})
    if settings.get("award_voting_mode", "direct") != "vote":
        return
    candidates = award_candidates(data, award)
    st.markdown(f"##### Vot pentru {award['titlu']}")
    if len(candidates) < 5:
        st.info("Sunt necesari cel puțin cinci jucători eligibili pentru acest vot.")
        return
    voter_id = award_voter_id(username, guest_invite)
    if not voter_id:
        st.info("Intră în cont sau accesează liga prin invitație pentru a vota.")
        return
    ballots = data.get("voturi_premii", {}).get(award["cheie"], {})
    previous = ballots.get(voter_id, {}) if isinstance(ballots, dict) else {}
    previous_choices = previous.get("alegeri", []) if isinstance(previous, dict) else []
    if not settings.get("award_voting_open"):
        st.info("Votul este închis de proprietarul sau editorul ligii.")
        scores = award_vote_scores(data, award["cheie"])
        if scores:
            ordered_scores = sorted(scores.items(), key=lambda item: (-item[1], item[0][1].casefold(), item[0][0].casefold()))
            render_cards([{"Loc": index + 1, "Jucător": player, "Echipă": team, "Puncte": score}
                          for index, ((team, player), score) in enumerate(ordered_scores)])
            best = ordered_scores[0][1]
            winners = [f"{player} · {team}" for (team, player), score in ordered_scores if score == best]
            st.caption(f"Câștigător: {' / '.join(winners)} · {best} puncte" if len(winners) == 1
                       else f"Egalitate la primul loc · {best} puncte")
        return
    st.caption("Alege cinci jucători în ordinea preferinței: locul 1 primește 5 puncte, apoi 4, 3, 2 și 1.")
    labels = {choice: f"{choice[1]} · {choice[0]}" for choice in candidates}
    ballot_key = safe_slug(widget_key or award["cheie"])
    with st.form(f"award_ballot_{ballot_key}"):
        choices = []
        for index in range(5):
            saved = previous_choices[index] if index < len(previous_choices) else {}
            saved_choice = (saved.get("echipa"), saved.get("jucator")) if isinstance(saved, dict) else None
            default_index = candidates.index(saved_choice) if saved_choice in candidates else index
            if touch_friendly:
                with st.container(key=f"spectator_award_picker_{ballot_key}_{index}"):
                    choice = st.radio(f"Locul {index + 1} · {5 - index} puncte", candidates,
                        index=default_index, format_func=lambda item: labels[item],
                        key=f"{ballot_key}_rank_{index}")
            else:
                choice = st.selectbox(f"Locul {index + 1} · {5 - index} puncte", candidates,
                    index=default_index, format_func=lambda item: labels[item],
                    key=f"{ballot_key}_rank_{index}")
            choices.append(choice)
        submit = st.form_submit_button("Salvează votul", type="primary")
    if submit:
        if len(set(choices)) != 5:
            st.error("Alege cinci jucători diferiți.")
        else:
            try:
                save_award_ballot(path, award["cheie"], choices, username, guest_invite)
                st.success("Votul a fost salvat. Îl poți modifica până la închiderea votului.")
                st.rerun()
            except Exception as exc:
                st.error(f"Nu am putut salva votul: {exc}")
    st.caption(f"Voturi înregistrate: {len(ballots) if isinstance(ballots, dict) else 0}")


def trofee_echipa(data, team):
    return [award["trofeu"] for award in definitii_premii(data)
            if award["tip"] == "echipa" and any(winner_team == team
                for winner_team, _ in award_winners(data, award))]


def trofee_jucator(data, team, player):
    return [award["trofeu"] for award in definitii_premii(data)
            if award["tip"] == "jucator" and (team, player) in award_winners(data, award)]


def propagate_cup_byes(cup):
    if not cup.get("runde"):
        return
    for index, slot in enumerate(cup["runde"][0]["meciuri"]):
        if slot.get("meci") is None and bool(slot.get("e1")) != bool(slot.get("e2")):
            slot["castigator"] = slot.get("e1") or slot.get("e2")
            advance_cup_winner(cup, 0, index)


def clear_cup_result(cup, round_index, match_index):
    removed = []
    while True:
        slot = cup["runde"][round_index]["meciuri"][match_index]
        if slot.get("meci"):
            removed.append(slot["meci"])
        if slot.get("meci_retur"):
            removed.append(slot["meci_retur"])
        slot["meci"], slot["meci_retur"] = None, None
        slot["castigator"], slot["penalti"] = None, False
        if round_index + 1 >= len(cup["runde"]):
            break
        next_slot = cup["runde"][round_index + 1]["meciuri"][match_index // 2]
        next_slot["e1" if match_index % 2 == 0 else "e2"] = None
        if next_slot.get("meci") is None:
            break
        round_index, match_index = round_index + 1, match_index // 2
    cup["castigatoare"] = None
    cup["status"] = "în desfășurare"
    return removed


def apply_player_stats(data, team_name, player_stats, sign=1):
    """Apply player stats while keeping a transferred player's history with them."""
    for player, values in player_stats.items():
        team, name = team_name, player
        visited = {team}
        while True:
            transfer = next((t for t in reversed(data.get("transferuri", []))
                             if t.get("de_la") == team and t.get("jucator", "").casefold() == name.casefold()), None)
            if not transfer or transfer.get("la") in visited:
                break
            team, name = transfer["la"], transfer.get("nume_nou", player)
            visited.add(team)
        if team not in data["echipe"]:
            continue
        target = data["echipe"][team]["jucatori"].setdefault(name, dict(STATS_JUCATOR))
        for key in STATS_JUCATOR:
            target[key] = max(0, target.get(key, 0) + sign * values.get(key, 0))


def transfer_player(data, player, source, destination, new_name=None):
    if source == destination:
        raise ValueError("Alege două echipe diferite.")
    source_roster = data["echipe"][source]["jucatori"]
    destination_roster = data["echipe"][destination]["jucatori"]
    if player not in source_roster:
        raise ValueError("Jucătorul nu mai este în lotul sursă.")
    final_name = (new_name or player).strip()
    if not final_name:
        final_name = player
    if final_name in destination_roster:
        raise ValueError(f"{destination} are deja un jucător numit «{final_name}».")
    destination_roster[final_name] = source_roster.pop(player)
    data["transferuri"].append({"jucator": player, "nume_nou": final_name,
        "de_la": source, "la": destination, "data": dt.date.today().strftime("%d.%m.%Y")})
    for chosen in data.get("premii_alese", {}).values():
        if chosen.get("echipa") == source and chosen.get("jucator") == player:
            chosen["echipa"], chosen["jucator"] = destination, final_name
    return final_name


def rename_team(data, old_name, new_name):
    new_name = new_name.strip()
    if not new_name or new_name == old_name:
        raise ValueError("Introdu un nume nou pentru echipă.")
    if new_name in data["echipe"]:
        raise ValueError("Există deja o echipă cu acest nume.")
    data["echipe"][new_name] = data["echipe"].pop(old_name)
    for match in data["istoric_meciuri"]:
        if match.get("e1") == old_name: match["e1"] = new_name
        if match.get("e2") == old_name: match["e2"] = new_name
        if match.get("masa_verde") == old_name: match["masa_verde"] = new_name
        for event in match.get("evenimente", []):
            if event.get("echipa") == old_name: event["echipa"] = new_name
    for fixture in data["program"]:
        if fixture.get("e1") == old_name: fixture["e1"] = new_name
        if fixture.get("e2") == old_name: fixture["e2"] = new_name
    for transfer in data.get("transferuri", []):
        if transfer.get("de_la") == old_name: transfer["de_la"] = new_name
        if transfer.get("la") == old_name: transfer["la"] = new_name
    for chosen in data.get("premii_alese", {}).values():
        if chosen.get("echipa") == old_name:
            chosen["echipa"] = new_name
    for cup in data.get("cupe", []):
        if cup.get("castigatoare") == old_name: cup["castigatoare"] = new_name
        cup["echipe"] = [new_name if team == old_name else team for team in cup.get("echipe", [])]
        for round_data in cup.get("runde", []):
            for slot in round_data.get("meciuri", []):
                if slot.get("e1") == old_name: slot["e1"] = new_name
                if slot.get("e2") == old_name: slot["e2"] = new_name
                if slot.get("castigator") == old_name: slot["castigator"] = new_name
                for match in (slot.get("meci"), slot.get("meci_retur")):
                    if not match:
                        continue
                    if match.get("e1") == old_name: match["e1"] = new_name
                    if match.get("e2") == old_name: match["e2"] = new_name
                    if match.get("masa_verde") == old_name: match["masa_verde"] = new_name
                    for event in match.get("evenimente", []):
                        if event.get("echipa") == old_name: event["echipa"] = new_name


def apply_match(data, match):
    for team_name in (match["e1"], match["e2"]):
        data["echipe"].setdefault(team_name, {"jucatori": {}, **STATS_ECHIPA})
    for name, gf, ga in ((match["e1"], match["goluri_e1"], match["goluri_e2"]),
                         (match["e2"], match["goluri_e2"], match["goluri_e1"])):
        team = data["echipe"][name]
        team["meciuri_jucate"] += 1
        team["goluri_marcate"] += gf
        team["goluri_primite"] += ga
        team["puncte"] += 3 if gf > ga else (1 if gf == ga else 0)
    data["istoric_meciuri"].append(match)
    apply_player_stats(data, match["e1"], match.get("mod_e1", {}))
    apply_player_stats(data, match["e2"], match.get("mod_e2", {}))


def rebuild_stats(data):
    for team in data["echipe"].values():
        team.update(STATS_ECHIPA)
        for stats in team["jucatori"].values():
            stats.update(STATS_JUCATOR)
    for match in data["istoric_meciuri"]:
        for name, gf, ga, key in ((match["e1"], match["goluri_e1"], match["goluri_e2"], "mod_e1"),
                                  (match["e2"], match["goluri_e2"], match["goluri_e1"], "mod_e2")):
            team = data["echipe"].setdefault(name, {"jucatori": {}, **STATS_ECHIPA})
            team["meciuri_jucate"] += 1
            team["goluri_marcate"] += gf
            team["goluri_primite"] += ga
            team["puncte"] += 3 if gf > ga else (1 if gf == ga else 0)
            apply_player_stats(data, name, match.get(key, {}))
    for cup in data.get("cupe", []):
        for round_data in cup.get("runde", []):
            for slot in round_data.get("meciuri", []):
                for match in (slot.get("meci"), slot.get("meci_retur")):
                    if match:
                        apply_player_stats(data, match["e1"], match.get("mod_e1", {}))
                        apply_player_stats(data, match["e2"], match.get("mod_e2", {}))
    for team in data["echipe"].values():
        for stats in team.get("jucatori", {}).values():
            adjustments = stats.get("_ajustari_statistici", {})
            if isinstance(adjustments, dict):
                for key in STATS_JUCATOR:
                    stats[key] = max(0, int(stats.get(key, 0) or 0) +
                                     int(adjustments.get(key, 0) or 0))


def generate_rounds(teams, home_away=False):
    rotating = list(teams)
    if len(rotating) < 2:
        return []
    if len(rotating) % 2:
        rotating.append(None)
    rounds = []
    for round_index in range(len(rotating) - 1):
        fixtures = []
        for i in range(len(rotating) // 2):
            one, two = rotating[i], rotating[-1 - i]
            if one is not None and two is not None:
                if (round_index + i) % 2:
                    one, two = two, one
                fixtures.append({"id": uuid.uuid4().hex[:8], "etapa": round_index + 1,
                                 "e1": one, "e2": two, "data": "", "meci_id": None,
                                 "arbitraj_cod": new_referee_code()})
        rounds.append(fixtures)
        rotating = [rotating[0], rotating[-1], *rotating[1:-1]]
    if home_away:
        for round_index, fixtures in enumerate(copy.deepcopy(rounds), start=len(rounds) + 1):
            rounds.append([{**f, "id": uuid.uuid4().hex[:8], "etapa": round_index,
                            "e1": f["e2"], "e2": f["e1"]} for f in fixtures])
    return [fixture for round_fixtures in rounds for fixture in round_fixtures]


def ranking(data):
    rows = []
    for name, team in data["echipe"].items():
        rows.append({"Echipă": name, "MJ": team["meciuri_jucate"], "V": 0, "E": 0, "Î": 0,
                     "GM": team["goluri_marcate"], "GP": team["goluri_primite"],
                     "DG": team["goluri_marcate"] - team["goluri_primite"], "Pct": team["puncte"],
                     "Formă": []})
    mapped = {row["Echipă"]: row for row in rows}
    for match in data["istoric_meciuri"]:
        if match["e1"] not in mapped or match["e2"] not in mapped:
            continue
        a, b = mapped[match["e1"]], mapped[match["e2"]]
        if match["goluri_e1"] > match["goluri_e2"]:
            a["V"] += 1; b["Î"] += 1
            a["Formă"].append("V"); b["Formă"].append("Î")
        elif match["goluri_e1"] < match["goluri_e2"]:
            b["V"] += 1; a["Î"] += 1
            b["Formă"].append("V"); a["Formă"].append("Î")
        else:
            a["E"] += 1; b["E"] += 1
            a["Formă"].append("E"); b["Formă"].append("E")
    for row in rows:
        row["Formă"] = " · ".join(row["Formă"][-5:]) or "–"
    return sorted(rows, key=lambda x: (-x["Pct"], -x["DG"], -x["GM"], x["Echipă"]))


def player_leaderboard(data, stat_key, label):
    players = [(player, team_name, stats.get(stat_key, 0))
               for team_name, team in data["echipe"].items()
               for player, stats in team.get("jucatori", {}).items()
               if stats.get(stat_key, 0) > 0]
    players.sort(key=lambda item: (-item[2], item[0].casefold(), item[1].casefold()))
    return [{"Loc": {1: "🥇", 2: "🥈", 3: "🥉"}.get(index, str(index)),
             "Jucător": player, "Echipă": team, label: value}
            for index, (player, team, value) in enumerate(players, 1)]


def _stage_sort_key(item):
    original_index, record = item
    stage = record.get("etapa")
    try:
        stage_number = int(stage)
    except (TypeError, ValueError):
        return (1, original_index, original_index)
    if stage_number <= 0:
        return (1, original_index, original_index)
    return (0, stage_number, original_index)


def ordered_by_stage(records):
    """Sort numbered rounds first; keep original order for records without a round."""
    return [record for _, record in sorted(enumerate(records), key=_stage_sort_key)]


def pending_fixtures(data):
    """Return scheduled fixtures that do not correspond to a recorded league match."""
    fixtures = data.get("program", [])
    matches = data.get("istoric_meciuri", [])
    match_ids = {str(match.get("id")) for match in matches if match.get("id") is not None}
    remaining = [match for match in matches]
    pending = []
    for fixture in fixtures:
        fixture_match_id = fixture.get("meci_id")
        if fixture_match_id and str(fixture_match_id) in match_ids:
            linked = next((match for match in remaining
                           if str(match.get("id")) == str(fixture_match_id)), None)
            if linked:
                remaining.remove(linked)
            continue
        fixture_teams = {fixture.get("e1"), fixture.get("e2")}
        played_index = next((index for index, match in enumerate(remaining)
            if {match.get("e1"), match.get("e2")} == fixture_teams
            and (fixture.get("etapa") is None or match.get("etapa") is None
                 or str(fixture.get("etapa")) == str(match.get("etapa")))), None)
        if played_index is None:
            pending.append(fixture)
        else:
            remaining.pop(played_index)
    return ordered_by_stage(pending)


def new_referee_code():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(8))


def _fixture_for_id(data, fixture_id):
    return next((item for item in data.get("program", [])
                 if str(item.get("id")) == str(fixture_id)), None)


def save_referee_state(path, fixture_id, access_code, live, finish=False):
    """Persist the state of only the match whose referee code was supplied."""
    code = str(access_code or "").strip().upper()
    if len(code) != 8:
        raise ValueError("Codul de arbitraj nu este valid.")
    fresh = load_league(path)
    fixture = _fixture_for_id(fresh, fixture_id)
    saved_code = str(fixture.get("arbitraj_cod", "")) if fixture else ""
    if not fixture or not saved_code or not hmac.compare_digest(saved_code, code):
        raise ValueError("Codul nu mai este valabil pentru acest meci.")
    updated_live = copy.deepcopy(live)
    finish = finish or updated_live.get("faza") == "final"
    if finish:
        if not fixture.get("meci_id"):
            match = build_match(fixture.get("e1", "Gazde"), fixture.get("e2", "Oaspeți"),
                                updated_live.get("evenimente", []), fixture.get("etapa"))
            apply_match(fresh, match)
            fixture["meci_id"] = match["id"]
        updated_live["faza"] = "final"
        updated_live["pornit_la"] = None
    fixture["arbitraj_live"] = updated_live
    _store_league(path, fresh)


def _live_match_score(data, fixture, live):
    if fixture.get("meci_id") and live.get("faza") == "final":
        recorded = next((item for item in data.get("istoric_meciuri", [])
                         if str(item.get("id")) == str(fixture.get("meci_id"))), None)
        if recorded:
            return int(recorded.get("goluri_e1", 0)), int(recorded.get("goluri_e2", 0))
    preview = build_match(fixture.get("e1", "Gazde"), fixture.get("e2", "Oaspeți"),
                          live.get("evenimente", []), fixture.get("etapa"))
    return preview["goluri_e1"], preview["goluri_e2"]


def _live_clock(live):
    """Return (display, numeric minute, effective stage, elapsed seconds)."""
    half = max(1, int(live.get("half_minutes", 45) or 45))
    stage = live.get("faza", "programat")
    elapsed = max(0, int(live.get("secunde", 0) or 0))
    started = live.get("pornit_la")
    if started:
        try:
            start_dt = dt.datetime.fromisoformat(str(started).replace("Z", "+00:00"))
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=dt.timezone.utc)
            elapsed += max(0, int((dt.datetime.now(dt.timezone.utc) - start_dt).total_seconds()))
        except (TypeError, ValueError):
            pass
    effective = stage
    added = max(0, int(live.get("minute_extra", 0) or 0))
    if stage in {"repriza1", "repriza2"} and elapsed >= half * 60:
        elapsed = half * 60
        effective = "repriza1_expirata" if stage == "repriza1" else "repriza2_expirata"
    elif stage in {"prelungiri1", "prelungiri2"} and elapsed >= added * 60:
        effective = "prelungiri1_expirate" if stage == "prelungiri1" else "prelungiri2_expirate"
    if stage == "repriza1":
        minute = min(half, elapsed // 60 + 1)
        shown = f"{minute}′"
        number = minute
    elif stage == "prelungiri1":
        extra_elapsed = elapsed // 60 + 1
        shown = f"{half}+{extra_elapsed}′"
        number = half + extra_elapsed
    elif stage in {"pauza", "repriza2", "prelungiri2", "repriza2_expirata", "prelungiri2_expirate"}:
        if stage in {"prelungiri2", "prelungiri2_expirate"}:
            extra_elapsed = elapsed // 60 + 1
            shown = f"{half * 2}+{extra_elapsed}′"
            number = half * 2 + extra_elapsed
        else:
            minute = min(half, elapsed // 60) if stage != "pauza" else 0
            second_half_minute = min(half * 2, half + minute + 1)
            shown = f"{second_half_minute}′" if stage != "pauza" else "Pauză"
            number = second_half_minute
    elif stage == "prelungiri1_expirate":
        shown, number = f"{half}+{added}′", half + added
    elif stage == "repriza1_expirata":
        shown, number = f"{half}′", half
    elif stage == "final_așteptare":
        shown, number = f"{half * 2}′", half * 2
    elif stage == "final":
        shown, number = "Final", half * 2 + int(live.get("minute_extra_total", 0) or 0)
    else:
        shown, number = "—", 1
    return shown, max(1, int(number)), effective, elapsed


def _live_clock_text(live):
    half = max(1, int(live.get("half_minutes", 45) or 45))
    stage = live.get("faza", "programat")
    _, _, _, elapsed = _live_clock(live)
    minutes, seconds = divmod(elapsed, 60)
    if stage == "repriza2":
        minute = min(half * 2, half + minutes)
        return f"{minute:02d}:{seconds:02d}"
    if stage == "prelungiri1":
        return f"{half}+{minutes:02d}:{seconds:02d}"
    if stage == "prelungiri2":
        return f"{half * 2}+{minutes:02d}:{seconds:02d}"
    if stage == "pauza":
        return "Pauză"
    if stage == "final_așteptare":
        return f"{half * 2:02d}:00"
    if stage == "final":
        return "Final"
    return f"{minutes:02d}:{seconds:02d}"


def _live_event_minute(live, phase, elapsed):
    """Map elapsed seconds to the football minute interval, rounding up."""
    half = max(1, int(live.get("half_minutes", 45) or 45))
    minute_in_period = int(elapsed) // 60 + 1
    if phase == "repriza1":
        minute = min(half, minute_in_period)
        return minute, f"{minute}′"
    if phase == "prelungiri1":
        return half + minute_in_period, f"{half}+{minute_in_period}′"
    if phase == "repriza2":
        minute = min(half * 2, half + minute_in_period)
        return minute, f"{minute}′"
    if phase == "prelungiri2":
        return half * 2 + minute_in_period, f"{half * 2}+{minute_in_period}′"
    return minute_in_period, f"{minute_in_period}′"


def _live_set_running(live, running):
    if running:
        if not live.get("pornit_la"):
            live["pornit_la"] = dt.datetime.now(dt.timezone.utc).isoformat()
    else:
        _, _, _, elapsed = _live_clock(live)
        live["secunde"] = elapsed
        live["pornit_la"] = None


@st.fragment(run_every=2)
def render_live_arbitration(path, fixture_id, can_edit, referee_code=None):
    data = load_league(path)
    fixture = _fixture_for_id(data, fixture_id)
    if not fixture:
        st.warning("Meciul nu mai există în program.")
        return
    live = fixture.setdefault("arbitraj_live", {
        "faza": "programat", "half_minutes": 45, "secunde": 0,
        "minute_extra": 0, "minute_extra_total": 0, "pornit_la": None,
        "evenimente": [],
    })
    live.setdefault("evenimente", [])
    live.setdefault("half_minutes", 45)
    live.setdefault("secunde", 0)
    live.setdefault("faza", "programat")
    live.setdefault("pornit_la", None)
    if can_edit and not referee_code:
        referee_code = str(fixture.get("arbitraj_cod", ""))
    home, away = fixture.get("e1", "Gazde"), fixture.get("e2", "Oaspeți")
    shown_minute, minute_number, effective_stage, elapsed = _live_clock(live)
    goals_home, goals_away = _live_match_score(data, fixture, live)
    st.markdown(f"### {home}  **{goals_home} – {goals_away}**  {away}")
    status_labels = {
        "programat": "Meciul nu a început", "repriza1": "Prima repriză",
        "repriza1_expirata": "Timpul primei reprize s-a încheiat",
        "prelungiri1": "Prelungiri · prima repriză",
        "prelungiri1_expirate": "Timpul suplimentar setat s-a scurs",
        "pauza": "Pauză", "repriza2": "A doua repriză",
        "repriza2_expirata": "Timpul reprizei a doua s-a încheiat",
        "prelungiri2": "Prelungiri · repriza a doua",
        "prelungiri2_expirate": "Timpul suplimentar setat s-a scurs",
        "final_așteptare": "Așteaptă fluierul final",
        "final": "Meci încheiat",
    }
    clock_col, phase_col = st.columns([1, 2])
    clock_col.metric("Cronometru", _live_clock_text(live))
    phase_col.metric("Stare", status_labels.get(effective_stage, status_labels.get(live["faza"], "În desfășurare")))
    st.caption(f"Minutul meciului: {shown_minute}")
    if can_edit:
        key = safe_slug(str(fixture_id))
        phase = live.get("faza", "programat")
        if phase == "programat":
            with st.form(f"referee_setup_{key}"):
                half_minutes = st.number_input("Durata unei reprize (minute)", min_value=1,
                    max_value=90, value=int(live.get("half_minutes", 45)), step=1,
                    key=f"ref_half_len_{key}")
                start_match = st.form_submit_button("Pornește prima repriză", type="primary")
            if start_match:
                live["half_minutes"] = int(half_minutes)
                live["faza"] = "repriza1"
                live["secunde"] = 0
                live["pornit_la"] = dt.datetime.now(dt.timezone.utc).isoformat()
                fixture["arbitraj_live"] = live
                save_referee_state(path, fixture_id, referee_code, live)
                st.rerun()
        elif phase == "repriza1" and effective_stage == "repriza1":
            if live.get("pornit_la"):
                if st.button("⏸ Pune cronometrul pe pauză", key=f"ref_pause_{key}"):
                    _live_set_running(live, False); fixture["arbitraj_live"] = live
                    save_referee_state(path, fixture_id, referee_code, live); st.rerun()
            elif st.button("▶ Continuă cronometrul", key=f"ref_resume_{key}"):
                _live_set_running(live, True); fixture["arbitraj_live"] = live
                save_referee_state(path, fixture_id, referee_code, live); st.rerun()
        elif effective_stage == "repriza1_expirata":
            with st.form(f"ref_added1_{key}"):
                added = st.number_input("Minute de prelungire pentru prima repriză", min_value=0,
                    max_value=15, value=int(live.get("minute_extra", 0)), step=1,
                    key=f"ref_extra1_{key}")
                set_added = st.form_submit_button("Salvează și pornește prelungirile", type="primary")
            if set_added:
                live["minute_extra"] = int(added)
                live["secunde"] = 0
                live["faza"] = "prelungiri1"
                live["pornit_la"] = dt.datetime.now(dt.timezone.utc).isoformat()
                fixture["arbitraj_live"] = live; save_referee_state(path, fixture_id, referee_code, live); st.rerun()
        elif phase == "prelungiri1" and effective_stage == "prelungiri1":
            actions = st.columns(2)
            if live.get("pornit_la"):
                if actions[0].button("⏸ Pauză", key=f"ref_extra1_pause_{key}"):
                    _live_set_running(live, False); fixture["arbitraj_live"] = live
                    save_referee_state(path, fixture_id, referee_code, live); st.rerun()
            elif actions[0].button("▶ Continuă prelungirile", key=f"ref_extra1_resume_{key}"):
                _live_set_running(live, True); fixture["arbitraj_live"] = live
                save_referee_state(path, fixture_id, referee_code, live); st.rerun()
            if actions[1].button("Intră la pauză", key=f"ref_halftime_{key}"):
                _live_set_running(live, False); live["faza"] = "pauza"
                live["minute_extra_total"] = int(live.get("minute_extra_total", 0)) + int(live.get("minute_extra", 0))
                live["minute_extra"] = 0
                fixture["arbitraj_live"] = live; save_referee_state(path, fixture_id, referee_code, live); st.rerun()
        elif phase == "prelungiri1" and effective_stage == "prelungiri1_expirate":
            st.info("Timpul suplimentar s-a scurs. Cronometrul continuă să ruleze; înregistrează ce se mai întâmplă, apoi închide repriza.")
            if not live.get("pornit_la") and st.button("▶ Continuă cronometrul", key=f"ref_extra1_continue_after_limit_{key}"):
                _live_set_running(live, True); fixture["arbitraj_live"] = live
                save_referee_state(path, fixture_id, referee_code, live); st.rerun()
            if st.button("Intră la pauză", type="primary", key=f"ref_halftime_done_{key}"):
                _live_set_running(live, False)
                live["faza"] = "pauza"
                live["minute_extra_total"] = int(live.get("minute_extra_total", 0)) + int(live.get("minute_extra", 0))
                live["minute_extra"] = 0; fixture["arbitraj_live"] = live
                save_referee_state(path, fixture_id, referee_code, live); st.rerun()
        elif phase == "pauza":
            if st.button("▶ Pornește repriza a doua", type="primary", key=f"ref_second_start_{key}"):
                live["faza"] = "repriza2"; live["secunde"] = 0
                live["pornit_la"] = dt.datetime.now(dt.timezone.utc).isoformat()
                fixture["arbitraj_live"] = live; save_referee_state(path, fixture_id, referee_code, live); st.rerun()
        elif phase == "repriza2" and effective_stage == "repriza2":
            if live.get("pornit_la"):
                if st.button("⏸ Pune cronometrul pe pauză", key=f"ref_pause2_{key}"):
                    _live_set_running(live, False); fixture["arbitraj_live"] = live
                    save_referee_state(path, fixture_id, referee_code, live); st.rerun()
            elif st.button("▶ Continuă cronometrul", key=f"ref_resume2_{key}"):
                _live_set_running(live, True); fixture["arbitraj_live"] = live
                save_referee_state(path, fixture_id, referee_code, live); st.rerun()
        elif effective_stage == "repriza2_expirata":
            with st.form(f"ref_added2_{key}"):
                added = st.number_input("Minute de prelungire pentru repriza a doua", min_value=0,
                    max_value=15, value=0, step=1, key=f"ref_extra2_{key}")
                set_added = st.form_submit_button("Salvează și pornește prelungirile", type="primary")
            if set_added:
                live["minute_extra"] = int(added)
                live["secunde"] = 0
                live["faza"] = "prelungiri2"
                live["pornit_la"] = dt.datetime.now(dt.timezone.utc).isoformat()
                fixture["arbitraj_live"] = live; save_referee_state(path, fixture_id, referee_code, live); st.rerun()
        elif phase == "prelungiri2" and effective_stage == "prelungiri2":
            actions = st.columns(2)
            if live.get("pornit_la"):
                if actions[0].button("⏸ Pauză", key=f"ref_extra2_pause_{key}"):
                    _live_set_running(live, False); fixture["arbitraj_live"] = live
                    save_referee_state(path, fixture_id, referee_code, live); st.rerun()
            elif actions[0].button("▶ Continuă prelungirile", key=f"ref_extra2_resume_{key}"):
                _live_set_running(live, True); fixture["arbitraj_live"] = live
                save_referee_state(path, fixture_id, referee_code, live); st.rerun()
        elif phase in {"final_așteptare", "prelungiri2"} and effective_stage in {"final_așteptare", "prelungiri2_expirate"}:
            if effective_stage == "prelungiri2_expirate":
                st.info("Timpul suplimentar s-a scurs. Cronometrul continuă să ruleze; înregistrează ce se mai întâmplă, apoi închide meciul.")
                if phase == "prelungiri2" and not live.get("pornit_la") and st.button(
                        "▶ Continuă cronometrul", key=f"ref_extra2_continue_after_limit_{key}"):
                    _live_set_running(live, True); fixture["arbitraj_live"] = live
                    save_referee_state(path, fixture_id, referee_code, live); st.rerun()
            if st.button("🏁 Închide meciul și salvează rezultatul", type="primary", key=f"ref_finish_{key}"):
                live["faza"] = "final"; live["pornit_la"] = None
                fixture["arbitraj_live"] = live
                save_referee_state(path, fixture_id, referee_code, live); st.rerun()
        if phase in {"repriza1", "prelungiri1", "repriza2", "prelungiri2"} and effective_stage in {
                "repriza1", "prelungiri1", "repriza2", "prelungiri2"}:
            if phase == "prelungiri1" and st.button("Marchează pauza", key=f"ref_halftime_manual_{key}"):
                _live_set_running(live, False); live["faza"] = "pauza"
                live["minute_extra_total"] = int(live.get("minute_extra_total", 0)) + int(live.get("minute_extra", 0))
                live["minute_extra"] = 0; fixture["arbitraj_live"] = live
                save_referee_state(path, fixture_id, referee_code, live); st.rerun()
        can_record = phase in {"repriza1", "prelungiri1", "repriza2", "prelungiri2"} and (
            effective_stage not in {"repriza1_expirata", "repriza2_expirata"})
        if can_record:
            st.markdown("#### Înregistrează un eveniment")
            event_team = st.selectbox("Echipa", [home, away], key=f"ref_team_{key}")
            event_type = st.selectbox("Eveniment", TIPURI_EVENIMENT, key=f"ref_type_{key}")
            roster = list(data.get("echipe", {}).get(event_team, {}).get("jucatori", {}))
            live_events = live.get("evenimente", [])
            rule = data.get("setari_liga", {}).get("substitution_rule", "5_no_return")
            substitution_limit = 5 if rule.startswith("5_") else None
            allow_reentry = rule in {"5_return", "unlimited_return"}
            event_scope = f"{key}_{safe_slug(event_team)}_{safe_slug(event_type)}"
            team_subs = [event for event in live_events
                if event.get("tip") == "Schimbare" and event.get("echipa") == event_team]
            exited_players = {event.get("jucator") for event in team_subs if event.get("jucator")}
            outgoing_options = roster if allow_reentry else [name for name in roster if name not in exited_players]
            player_options = outgoing_options if event_type == "Schimbare" else [*roster, "Alt jucător…"]
            player = st.selectbox("Jucător" if event_type != "Schimbare" else "Jucător care iese",
                                  player_options or ["—"], key=f"ref_player_{event_scope}")
            manual_player = st.text_input("Numele jucătorului", key=f"ref_manual_{event_scope}") if player == "Alt jucător…" else ""
            player_name = manual_player.strip() if player == "Alt jucător…" else player
            assist = None
            if event_type in TIPURI_GOL:
                assists = ["Fără assist", *roster, "Alt jucător…"]
                assist_choice = st.selectbox("Assist (opțional)", assists, key=f"ref_assist_{event_scope}")
                assist = (st.text_input("Numele celui cu assist", key=f"ref_assist_manual_{event_scope}").strip() or None
                          if assist_choice == "Alt jucător…" else
                          (assist_choice if assist_choice != "Fără assist" else None))
            incoming = None
            if event_type == "Schimbare":
                incoming_options = [name for name in roster if name != player_name
                                    and (allow_reentry or name not in exited_players)]
                incoming = st.selectbox("Jucător care intră", incoming_options or ["—"], key=f"ref_incoming_{event_scope}")
                if substitution_limit is not None and len(team_subs) >= substitution_limit:
                    st.caption("Echipa a folosit deja toate schimbările permise pentru meci.")
            add_event = st.button("Adaugă acum", type="primary",
                disabled=(event_type == "Schimbare" and substitution_limit is not None
                          and len(team_subs) >= substitution_limit), key=f"ref_add_event_{key}")
            if add_event:
                if not player_name:
                    st.error("Alege sau completează numele jucătorului.")
                elif event_type == "Schimbare" and (not incoming or incoming == "—"):
                    st.error("Alege jucătorul care intră.")
                else:
                    event_minute, display_minute = _live_event_minute(live, phase, elapsed)
                    event = {"echipa": event_team, "minut": event_minute,
                             "afișaj_minut": display_minute, "tip": event_type,
                             "jucator": player_name}
                    if assist:
                        event["asist"] = assist
                    if event_type == "Schimbare":
                        event["intra"] = incoming
                    live.setdefault("evenimente", []).append(event)
                    fixture["arbitraj_live"] = live
                    save_referee_state(path, fixture_id, referee_code, live)
                    st.rerun()
    if live.get("evenimente"):
        st.markdown("#### Evenimente live")
        for event in reversed(live["evenimente"]):
            minute = event.get("afișaj_minut") or f"{event.get('minut', '—')}′"
            detail = f"**{minute}** · {event.get('echipa')} · {event.get('tip')} · {event.get('jucator')}"
            if event.get("tip") == "Schimbare":
                detail += f" → {event.get('intra', '—')}"
            if event.get("asist"):
                detail += f" · assist {event['asist']}"
            st.markdown(detail)
    else:
        st.caption("Evenimentele vor apărea aici în timp real.")


def render_viewer_arbitration(path, league_key_value):
    data = load_league(path)
    st.subheader("Arbitraj")
    st.caption("Introdu codul primit de la proprietarul sau editorul ligii ca să poți arbitra acel meci.")
    with st.form(f"viewer_referee_code_{safe_slug(league_key_value)}"):
        code = re.sub(r"[^A-Z0-9]", "", st.text_input("Codul meciului", max_chars=8).upper())
        enter = st.form_submit_button("Deschide meciul", type="primary")
    if enter:
        match = next((fixture for fixture in data.get("program", [])
            if hmac.compare_digest(str(fixture.get("arbitraj_cod", "")), code)
            and len(code) == 8), None)
        if not match:
            st.error("Codul nu este valid pentru această ligă.")
            st.session_state.pop("arbitraj_fixture_id", None)
            st.session_state.pop("arbitraj_league_key", None)
            st.session_state.pop("arbitraj_access_code", None)
        else:
            st.session_state["arbitraj_fixture_id"] = str(match.get("id"))
            st.session_state["arbitraj_league_key"] = league_key_value
            st.session_state["arbitraj_access_code"] = code
            st.rerun()
    fixture_id = st.session_state.get("arbitraj_fixture_id")
    if fixture_id and st.session_state.get("arbitraj_league_key") == league_key_value:
        fixture = _fixture_for_id(data, fixture_id)
        if fixture:
            render_live_arbitration(path, fixture_id, True,
                                    st.session_state.get("arbitraj_access_code"))
            if st.button("Închide arbitrajul", key=f"ref_close_{safe_slug(league_key_value)}"):
                st.session_state.pop("arbitraj_fixture_id", None)
                st.session_state.pop("arbitraj_league_key", None)
                st.session_state.pop("arbitraj_access_code", None)
                st.rerun()


def render_owner_arbitration(data, path, league_key_value):
    st.subheader("Arbitraj live")
    fixtures = data.get("program", [])
    if not fixtures:
        st.info("Adaugă mai întâi meciurile în Program, din «Meciuri și program».")
        return
    changed = False
    for fixture in fixtures:
        if not fixture.get("arbitraj_cod"):
            fixture["arbitraj_cod"] = new_referee_code()
            changed = True
        if "arbitraj_live" not in fixture:
            recorded_match = next((item for item in data.get("istoric_meciuri", [])
                                   if str(item.get("id")) == str(fixture.get("meci_id"))), None)
            fixture["arbitraj_live"] = {"faza": "final" if recorded_match else "programat", "half_minutes": 45,
                "secunde": 0, "minute_extra": 0, "minute_extra_total": 0,
                "pornit_la": None,
                "evenimente": copy.deepcopy(recorded_match.get("evenimente", [])) if recorded_match else []}
            changed = True
    if changed:
        save_league(path, data)
    st.caption("Codurile sunt vizibile doar proprietarului și editorilor. Trimite codul doar arbitrului ales pentru meci.")
    render_cards([{"Etapa": item.get("etapa") or "—", "Meci": f"{item.get('e1')} – {item.get('e2')}",
                   "Cod arbitraj": item["arbitraj_cod"],
                   "Stare": item.get("arbitraj_live", {}).get("faza", "programat")}
                  for item in ordered_by_stage(fixtures)])
    selected = st.selectbox("Alege meciul de arbitrat", ordered_by_stage(fixtures),
        format_func=lambda item: f"Etapa {item.get('etapa') or '—'} · {item.get('e1')} – {item.get('e2')}",
        key=f"referee_fixture_{safe_slug(league_key_value)}")
    render_live_arbitration(path, str(selected.get("id")), True)


@st.fragment(run_every=3)
def render_live_matches_overview(path):
    data = load_league(path)
    live_fixtures = [fixture for fixture in data.get("program", [])
        if fixture.get("arbitraj_live", {}).get("faza", "programat") not in {"programat", "final"}]
    if not live_fixtures:
        st.info("Nu există meciuri live în acest moment.")
        return
    st.caption("Scorul, cronometrul și evenimentele se actualizează automat.")
    for fixture in ordered_by_stage(live_fixtures):
        live = fixture.get("arbitraj_live", {})
        goals_home, goals_away = _live_match_score(data, fixture, live)
        shown, _, effective, _ = _live_clock(live)
        phase_names = {"repriza1": "Prima repriză", "repriza1_expirata": "Prelungiri — repriza 1",
            "prelungiri1": "Prelungiri — repriza 1", "prelungiri1_expirate": "Pauză",
            "pauza": "Pauză", "repriza2": "A doua repriză",
            "repriza2_expirata": "Prelungiri — repriza 2", "prelungiri2": "Prelungiri — repriza 2",
            "prelungiri2_expirate": "Fluier final în așteptare", "final_așteptare": "Fluier final în așteptare"}
        with st.container(border=True):
            st.markdown(f"### 🔴 {fixture.get('e1')}  **{goals_home} – {goals_away}**  {fixture.get('e2')}")
            st.caption(f"Etapa {fixture.get('etapa') or '—'} · {phase_names.get(effective, phase_names.get(live.get('faza'), 'În desfășurare'))} · {shown}")
            for event in reversed(live.get("evenimente", [])[-5:]):
                minute = event.get("afișaj_minut") or f"{event.get('minut', '—')}′"
                description = f"{minute} · {event.get('tip')} · {event.get('jucator')} ({event.get('echipa')})"
                if event.get("tip") == "Schimbare":
                    description += f" → {event.get('intra', '—')}"
                st.write(description)


def render_cards(rows):
    """Render compact, themed rows matching the original app's Treeview tables."""
    rows = list(rows)
    if not rows:
        st.caption("Nu există date de afișat încă.")
        return
    columns = list(dict.fromkeys(key for row in rows for key in row))
    head = "".join(f"<th>{html.escape(str(tr(column)))}</th>" for column in columns)
    body_rows = []
    for row in rows:
        cells = "".join(
            f"<td>{html.escape(str(tr(row.get(column)) if row.get(column) not in (None, '') else '–'))}</td>"
            for column in columns)
        body_rows.append(f"<tr>{cells}</tr>")
    markup = ("<div class='league-table-wrap'><table class='league-table'>"
              f"<thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody>"
              "</table></div>")
    st.markdown(markup, unsafe_allow_html=True)


def _match_records(data):
    yield from data.get("istoric_meciuri", [])
    for cup in data.get("cupe", []):
        for round_data in cup.get("runde", []):
            for slot in round_data.get("meciuri", []):
                for match in (slot.get("meci"), slot.get("meci_retur")):
                    if match:
                        yield match


def motm_wins_for_player(data, team, player):
    """Count matches where this player has the sole highest number of MOTM votes."""
    wins = 0
    for match in _match_records(data):
        votes = match.get("voturi_motm", {})
        if not isinstance(votes, dict) or not votes:
            continue
        counts = {}
        for vote in votes.values():
            if isinstance(vote, dict):
                candidate = (vote.get("echipa"), vote.get("jucator"))
            elif isinstance(vote, str) and "|" in vote:
                candidate = tuple(vote.split("|", 1))
            else:
                continue
            counts[candidate] = counts.get(candidate, 0) + 1
        own_votes = counts.get((team, player), 0)
        if own_votes and own_votes == max(counts.values()) and sum(
                1 for count in counts.values() if count == own_votes) == 1:
            wins += 1
    return wins


def _motm_voter(data, match, username=None, profile=None, guest_invite=None):
    teams = {match.get("e1"), match.get("e2")}
    mode = data.get("setari_liga", {}).get("motm_voting_mode", "no_players")
    if username:
        voter_id = "voter:" + hashlib.sha256(f"user:{username}".encode("utf-8")).hexdigest()
        selection = ((profile or {}).get("selectii_ligi", {}).get(
            st.session_state.get("entered_league", "")) or {})
        # The league key is not necessarily the current-session key for spectators;
        # use membership data as the authoritative fallback.
        selection = data.get("selectii_membri", {}).get(username) or selection
        member = next((item for item in data.get("membri", [])
                       if str(item.get("username", "")).casefold() == username.casefold()
                       and item.get("activ", True)), None)
        own_player = ((selection.get("echipa"), selection.get("jucator"))
                      if selection.get("echipa") and selection.get("jucator") else None)
        if member and member.get("tip") == "jucator" and not own_player:
            return voter_id, False, "Asociază-ți jucătorul în fila «Alegerea mea» înainte să votezi.", None
        if mode == "no_players" and own_player and own_player[0] in teams:
            return voter_id, False, "Jucătorii echipelor din acest meci nu pot vota.", own_player
        return voter_id, True, "", own_player
    if guest_invite:
        invitation = guest_invite.get("invitation", {})
        voter_id = "voter:" + hashlib.sha256(
            f"invite:{invitation.get('id')}".encode("utf-8")).hexdigest()
        selection = data.get("selectii_membri", {}).get(invitation.get("id"), {})
        team = selection.get("echipa") or invitation.get("echipa")
        own_player = ((team, selection.get("jucator"))
                      if team and selection.get("jucator") else None)
        if invitation.get("tip") == "jucator" and not own_player:
            return voter_id, False, "Asociază-ți jucătorul înainte să votezi.", None
        if mode == "no_players" and own_player and team in teams:
            return voter_id, False, "Jucătorii echipelor din acest meci nu pot vota.", own_player
        return voter_id, True, "", own_player
    voter_id = st.session_state.setdefault("motm_voter_id", f"spectator:{uuid.uuid4().hex}")
    return voter_id, True, "", None


def save_motm_vote(path, match_id, voter_id, team, player, username=None, guest_invite=None):
    fresh = load_league(path)
    if username:
        owner = Path(path).parent.name
        member = next((item for item in fresh.get("membri", [])
                       if str(item.get("username", "")).casefold() == username.casefold()
                       and item.get("activ", True)), None)
        if owner.casefold() != username.casefold() and not member:
            raise ValueError("Nu mai ai acces la această ligă.")
    elif guest_invite:
        invitation = guest_invite.get("invitation", {})
        active = next((item for item in fresh.get("invitatii", [])
                       if item.get("id") == invitation.get("id")
                       and hmac.compare_digest(str(item.get("token", "")),
                                               str(invitation.get("token", "")))
                       and item.get("activ", True)), None)
        if not active:
            raise ValueError("Invitația nu mai este activă.")
    else:
        raise ValueError("Trebuie să intri în ligă înainte să votezi.")

    target = next((item for item in _match_records(fresh)
                   if str(item.get("id", "")) == str(match_id)), None)
    if not target:
        raise ValueError("Meciul nu mai există.")
    if target.get("masa_verde"):
        raise ValueError("Nu se votează omul meciului pentru o victorie la masa verde.")
    if team not in (target.get("e1"), target.get("e2")):
        raise ValueError("Jucătorul ales nu aparține uneia dintre echipele meciului.")
    recorded_for_team = target.get("mod_e1", {}) if team == target.get("e1") else target.get("mod_e2", {})
    if (player not in fresh.get("echipe", {}).get(team, {}).get("jucatori", {})
            and player not in recorded_for_team):
        raise ValueError("Jucătorul ales nu mai există în lot.")
    _, eligible, reason, own_player = _motm_voter(fresh, target, username,
        load_users().get(username, {}) if username else None, guest_invite)
    if not eligible:
        raise ValueError(reason)
    if (fresh.get("setari_liga", {}).get("motm_voting_mode", "no_players") == "no_self_vote"
            and own_player == (team, player)):
        raise ValueError("Nu poți vota pentru propriul jucător.")
    target.setdefault("voturi_motm", {})[voter_id] = {"echipa": team, "jucator": player}
    _store_league(path, fresh)


def render_motm_voting(data, match, path, username=None, profile=None,
                       guest_invite=None, widget_key=None, touch_friendly=False):
    if not match.get("id"):
        st.caption("Votul nu este disponibil pentru acest meci.")
        return
    if match.get("masa_verde"):
        st.caption("Nu se votează omul meciului pentru o victorie la masa verde.")
        return
    teams = [match.get("e1"), match.get("e2")]
    candidates = [(team, player) for team in teams if team in data.get("echipe", {})
                  for player in data["echipe"][team].get("jucatori", {})]
    for team, stats_key in ((teams[0], "mod_e1"), (teams[1], "mod_e2")):
        candidates.extend((team, player) for player in match.get(stats_key, {})
                          if (team, player) not in candidates)
    st.markdown("**⭐ Omul meciului**")
    if not candidates:
        st.caption("Adaugă jucători în loturi pentru a putea vota.")
        return
    voter_id, eligible, reason, own_player = _motm_voter(data, match, username, profile, guest_invite)
    votes = match.get("voturi_motm", {})
    if not isinstance(votes, dict):
        votes = {}
    counts = {}
    for vote in votes.values():
        if isinstance(vote, dict):
            candidate = (vote.get("echipa"), vote.get("jucator"))
        elif isinstance(vote, str) and "|" in vote:
            candidate = tuple(vote.split("|", 1))
        else:
            continue
        if candidate in candidates:
            counts[candidate] = counts.get(candidate, 0) + 1
    total = sum(counts.values())
    if total:
        ordered = sorted(candidates, key=lambda candidate: (-counts.get(candidate, 0),
                                                              candidate[1].casefold(), candidate[0].casefold()))
        render_cards([{"Jucător": player, "Echipă": team, "Voturi": counts.get((team, player), 0)}
                      for team, player in ordered if counts.get((team, player), 0)])
        best = max(counts.values())
        leaders = [player for (team, player), count in counts.items() if count == best]
        st.caption((f"Lider la vot: {', '.join(leaders)} · {best} voturi · {total} voturi în total")
                   if len(leaders) == 1 else f"Egalitate la {best} voturi · {total} voturi în total")
    else:
        st.caption("Încă nu s-a votat.")
    if not eligible:
        st.info(reason)
        return
    if data.get("setari_liga", {}).get("motm_voting_mode", "no_players") == "no_self_vote" and own_player:
        candidates = [candidate for candidate in candidates if candidate != own_player]
        st.caption("Jucătorii pot vota, dar nu își pot alege propriul profil.")
        if not candidates:
            st.info("Nu există alți jucători eligibili pentru vot.")
            return
    labels = [f"{player} · {team}" for team, player in candidates]
    candidate_by_label = {f"{player} · {team}": (team, player) for team, player in candidates}
    previous = votes.get(voter_id, {})
    previous_label = (f"{previous.get('jucator')} · {previous.get('echipa')}"
                      if isinstance(previous, dict) else str(previous).replace("|", " · "))
    default_index = labels.index(previous_label) if previous_label in labels else 0
    suffix = widget_key or str(match["id"])
    with st.form(f"motm_vote_{safe_slug(str(suffix))}"):
        if touch_friendly:
            with st.container(key=f"spectator_motm_picker_{safe_slug(str(suffix))}"):
                selected_label = st.radio("Votează pentru", labels, index=default_index,
                    key=f"spectator_motm_choice_{safe_slug(str(suffix))}")
        else:
            selected_label = st.selectbox("Votează pentru", labels, index=default_index)
        submit_vote = st.form_submit_button("Trimite votul", type="primary")
    if submit_vote:
        team, player = candidate_by_label[selected_label]
        try:
            save_motm_vote(path, match["id"], voter_id, team, player, username, guest_invite)
            st.success("Votul tău a fost salvat. Îl poți schimba până când meciul este șters.")
            st.rerun()
        except Exception as exc:
            st.error(f"Nu am putut salva votul: {exc}")


def render_view_only(data, username, profile, entry, guest_invite=None, guest_profile=None):
    st.info("Acces de vizualizare · nu poți modifica această ligă.")
    if username:
        selection_key = league_key(entry)
        saved_selection = (profile.get("selectii_ligi", {}).get(selection_key) or
                           data.get("selectii_membri", {}).get(username, {}))
        if saved_selection.get("tip") == "jucator" or saved_selection.get("jucator"):
            st.success(f"Ai intrat ca jucător: {saved_selection.get('jucator')} · {saved_selection.get('echipa')}.")
            if st.session_state.get("player_profile_sync_error"):
                st.warning("Alegerea a fost salvată în ligă, dar nu s-a putut sincroniza cu profilul contului. Statisticile din ligă rămân disponibile.")
            player_stats = (data.get("echipe", {}).get(saved_selection.get("echipa"), {})
                            .get("jucatori", {}).get(saved_selection.get("jucator"), {}))
            if player_stats:
                stat_cols = st.columns(4)
                for col, label, key in zip(stat_cols, ("Goluri", "Assisturi", "Galbene", "Roșii"),
                        ("goluri", "asisturi", "cartonase_galbene", "cartonase_rosii")):
                    col.metric(label, player_stats.get(key, 0))
    can_choose_player = username or (guest_profile and guest_profile.get("kind") == "jucator") or (
        guest_invite and guest_invite.get("access_method") == "legacy"
        and guest_invite["invitation"].get("tip") == "jucator")
    tabs = st.tabs(["Clasament", "Statistici", "Loturi", "Meciuri și program", "Cupe", "Premii"] +
                   (["Alegerea mea"] if can_choose_player else []))
    t1, t2 = tabs[0], tabs[2]
    with t1:
        st.subheader(data.get("nume_liga", "Liga"))
        render_cards(ranking(data))
    with t2:
        for team, info in data["echipe"].items():
            with st.expander(f"{team} · {len(info.get('jucatori', {}))} jucători"):
                render_cards([{"Jucător": p, "Poziție": s.get("pozitie") or "–",
                               "Trofee": " · ".join(trofee_jucator(data, team, p)) or "–",
                               **{k: v for k, v in s.items() if k not in {"pozitie", "_ajustari_statistici"}}}
                              for p, s in info.get("jucatori", {}).items()])
    with tabs[3]:
        match_tabs = st.tabs(["Rezultate", "Program", "Live", "Arbitraj"])
        with match_tabs[0]:
            ordered_matches = ordered_by_stage(data.get("istoric_meciuri", []))
            if ordered_matches:
                with st.container(key="spectator_match_picker"):
                    selected_match = st.radio(
                        "Alege un meci",
                        ordered_matches,
                        format_func=lambda m: f"Etapa {m.get('etapa') or '—'} · {m.get('e1')} {m.get('goluri_e1', 0)}–{m.get('goluri_e2', 0)} {m.get('e2')}",
                        key=f"viewer_history_match_{safe_slug(league_key(entry))}")
                with st.container(border=True):
                    render_match_history_details(selected_match)
                    st.divider()
                    st.markdown("##### ⭐ Votează omul meciului")
                    render_motm_voting(data, selected_match, entry["path"], username, profile, guest_invite,
                        widget_key=f"viewer-{league_key(entry)}-{selected_match.get('id')}",
                        touch_friendly=True)
            else:
                st.info("Nu există încă meciuri înregistrate în această ligă.")
        with match_tabs[1]:
            fixtures = pending_fixtures(data)
            if fixtures:
                render_cards([{"Etapa": f.get("etapa"), "Gazdă": f.get("e1"), "Oaspeți": f.get("e2"),
                    "Data": f.get("data", ""), "Status": "Programat"} for f in fixtures])
            else:
                st.info("Nu există meciuri rămase în program.")
        with match_tabs[2]:
            st.subheader("Meciuri live")
            render_live_matches_overview(entry["path"])
        with match_tabs[3]:
            render_viewer_arbitration(entry["path"], league_key(entry))
    with tabs[4]:
        for cup in data.get("cupe", []):
            st.markdown(f"### {'🏅 ' if cup.get('super') else ''}{cup.get('nume', 'Cupa')} · {cup.get('status', '')}")
            for round_data in cup.get("runde", []):
                st.markdown(f"**{round_data.get('nume', 'Runda')}**")
                for slot in round_data.get("meciuri", []):
                    match = slot.get("meci")
                    if match:
                        substitutions = match_substitution_summary(match)
                        if substitutions != "–":
                            st.caption(f"Schimbări: {substitutions}")
                        if cup.get("tur_retur"):
                            st.write(f"Tur: {match['e1']} {match['goluri_e1']} – {match['goluri_e2']} {match['e2']}")
                            returned = slot.get("meci_retur")
                            if returned:
                                substitutions = match_substitution_summary(returned)
                                if substitutions != "–":
                                    st.caption(f"Schimbări retur: {substitutions}")
                                aggregate_home = match["goluri_e1"] + returned["goluri_e2"]
                                aggregate_away = match["goluri_e2"] + returned["goluri_e1"]
                                st.write(f"Retur: {returned['e1']} {returned['goluri_e1']} – {returned['goluri_e2']} {returned['e2']}")
                                st.caption(f"Scor agregat {match['e1']} {aggregate_home} – {aggregate_away} {match['e2']} · se califică {slot.get('castigator') or 'urmează returul'}")
                                render_motm_voting(data, returned, entry["path"], username, profile, guest_invite,
                                    widget_key=f"viewer-cup-{cup.get('id')}-{returned.get('id')}",
                                    touch_friendly=True)
                            else:
                                st.caption("Returul urmează.")
                        else:
                            st.write(f"{match['e1']} {match['goluri_e1']} – {match['goluri_e2']} {match['e2']} · câștigă {slot.get('castigator')}")
                        render_motm_voting(data, match, entry["path"], username, profile, guest_invite,
                            widget_key=f"viewer-cup-{cup.get('id')}-{match.get('id')}",
                            touch_friendly=True)
                    else:
                        st.write(f"{slot.get('e1') or '—'} vs {slot.get('e2') or 'așteaptă'}")
    with tabs[1]:
        st.subheader("Statistici jucători")
        stat_sections = (
            ("⚽ Marcatori", "goluri", "Goluri"),
            ("🎯 Asistenți", "asisturi", "Assisturi"),
            ("🟨 Galbene", "cartonase_galbene", "Galbene"),
            ("🟥 Roșii", "cartonase_rosii", "Roșii"),
        )
        for tab, (title, field, label) in zip(st.tabs([section[0] for section in stat_sections]), stat_sections):
            with tab:
                rows = player_leaderboard(data, field, label)
                if rows:
                    render_cards(rows)
                else:
                    st.info("Încă nu există date pentru acest top.")
    with tabs[5]:
        awards = []
        for award in definitii_premii(data):
            winners = award_winners(data, award)
            if award["tip"] == "echipa":
                winner_text = " / ".join(team for team, _ in winners)
            else:
                winner_text = " / ".join(f"{player} · {team}" for team, player in winners)
            awards.append({"Premiu": award["titlu"], "Câștigător": winner_text or "Neacordat"})
        render_cards(awards)
        if data.get("setari_liga", {}).get("award_voting_mode", "direct") == "vote":
            st.markdown("### Voturile pentru premiile individuale")
            for award in definitii_premii(data):
                if award["tip"] == "jucator" and not award_is_automatic(award):
                    with st.container(border=True):
                        render_award_ballot(data, award, entry["path"], username, guest_invite,
                            widget_key=f"viewer-{league_key(entry)}-{award['cheie']}",
                            touch_friendly=True)

    if can_choose_player:
        with tabs[6]:
            teams = list(data.get("echipe", {}))
            if username:
                st.write(f"{profile.get('nume', username)} · @{username} · {profile.get('pozitie', 'Poziție nespecificată')}")
                selection_key = league_key(entry)
                prior = (profile.get("selectii_ligi", {}).get(selection_key) or
                         data.get("selectii_membri", {}).get(username, {}))
                current_kind = "jucator" if prior.get("jucator") else "spectator"
                mode = st.radio("Cum vrei să apari în ligă?", ["Spectator", "Jucător"],
                    index=1 if current_kind == "jucator" else 0, horizontal=True,
                    key=f"viewer_kind_{safe_slug(entry['owner'])}_{safe_slug(entry['path'].stem)}")
                if mode == "Jucător":
                    if not teams:
                        st.info("Liga nu are încă echipe. Deocamdată poți rămâne spectator.")
                    else:
                        league_widget_id = f"{safe_slug(entry['owner'])}_{safe_slug(entry['path'].stem)}"
                        with st.container(key="spectator_profile_team_picker"):
                            team = st.radio("Echipa ta", teams,
                                index=teams.index(prior["echipa"]) if prior.get("echipa") in teams else 0,
                                key=f"viewer_team_{league_widget_id}")
                        players = list(data["echipe"][team].get("jucatori", {}))
                        if players:
                            with st.container(key="spectator_profile_player_picker"):
                                player = st.radio("Alege-ți jucătorul", players,
                                    index=players.index(prior["jucator"]) if prior.get("jucator") in players else 0,
                                    key=f"viewer_player_{league_widget_id}_{safe_slug(team)}")
                        else:
                            player = None
                        if not players:
                            st.caption("Echipa aleasă nu are încă jucători în lot.")
                        save_link = st.button("Salvează alegerea", type="primary",
                            disabled=not bool(players), key=f"save_viewer_player_{league_widget_id}")
                        if save_link and player:
                            try:
                                save_code_member_choice(entry, username, team, player)
                                st.success("Alegerea ta a fost salvată.")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Nu am putut salva alegerea: {exc}")
                elif current_kind == "jucator":
                    if st.button("Salvează ca spectator", key="save_viewer_spectator"):
                        try:
                            save_code_member_choice(entry, username)
                            st.success("Acum apari în ligă ca spectator.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Nu am putut salva alegerea: {exc}")
                else:
                    st.info("Ai intrat ca spectator. Poți alege «Jucător» oricând.")
                if st.session_state.get("player_profile_sync_error"):
                    st.warning("Alegerea este salvată în ligă, dar nu s-a sincronizat în profilul contului. Statisticile ligii rămân disponibile.")
            elif guest_profile:
                st.write(f"Profilul meu · **{guest_profile.get('player')}** · {guest_profile.get('team')}")
                prior = data.get("selectii_membri", {}).get(guest_profile.get("profile_id"), {})
                stats = data.get("echipe", {}).get(prior.get("echipa"), {}).get("jucatori", {}).get(prior.get("jucator"), {})
                if stats:
                    stat_cols = st.columns(4)
                    for col, title, field in zip(stat_cols, ("Goluri", "Assisturi", "Galbene", "Roșii"),
                            ("goluri", "asisturi", "cartonase_galbene", "cartonase_rosii")):
                        col.metric(title, stats.get(field, 0))
            else:
                invitation = guest_invite["invitation"]
                st.write(f"Invitație pentru **{invitation.get('nume', 'Jucător invitat')}** · jucător în ligă")
                selection_key = invitation.get("id")
                prior = data.get("selectii_membri", {}).get(selection_key, {})
                with st.container(key="spectator_invite_team_picker"):
                    team = st.radio("Echipa", teams,
                        index=teams.index(prior["echipa"]) if prior.get("echipa") in teams else 0,
                        key=f"spectator_invite_team_{safe_slug(str(selection_key))}")
                players = list(data["echipe"][team].get("jucatori", {}))
                if players:
                    with st.container(key="spectator_invite_player_picker"):
                        player = st.radio("Jucător din lot", players,
                            index=players.index(prior["jucator"]) if prior.get("jucator") in players else 0,
                            key=f"spectator_invite_player_{safe_slug(str(selection_key))}_{safe_slug(team)}")
                else:
                    player = None
                    st.caption("Echipa nu are jucători în lot încă.")
                with st.form("viewer_profile_link"):
                    save_link = st.form_submit_button("Salvează asocierea", disabled=not bool(players))
                if save_link and player:
                    if username:
                        users = load_users()
                        users[username].setdefault("selectii_ligi", {})[selection_key] = {
                            "echipa": team, "jucator": player, "pozitie": profile.get("pozitie", ""),
                            "actualizat": dt.datetime.now().timestamp()}
                        save_users(users)
                        st.success("Asocierea a fost salvată în profilul tău.")
                    else:
                        try:
                            save_guest_selection(entry["path"], guest_invite["invitation"], team, player)
                            st.success("Asocierea jucătorului invitat a fost salvată.")
                        except ValueError as exc:
                            st.error(str(exc))
                    st.rerun()
                if prior:
                    stats = data.get("echipe", {}).get(prior.get("echipa"), {}).get("jucatori", {}).get(prior.get("jucator"), {})
                    if stats:
                        st.metric("Goluri în această ligă", stats.get("goluri", 0))


def render_guest_player_choice(data, path, invitation):
    st.subheader("Alegerea mea în această ligă")
    st.caption(f"Invitat ca jucător: {invitation.get('nume', 'Invitat')}")
    teams = list(data.get("echipe", {}))
    if not teams:
        st.info("Liga nu are încă echipe.")
        return
    previous = data.get("selectii_membri", {}).get(invitation.get("id"), {})
    with st.container(key="spectator_legacy_team_picker"):
        team = st.radio("Echipa", teams,
            index=teams.index(previous["echipa"]) if previous.get("echipa") in teams else 0)
    players = list(data["echipe"][team].get("jucatori", {}))
    if players:
        with st.container(key="spectator_legacy_player_picker"):
            player = st.radio("Jucător", players,
                index=players.index(previous["jucator"]) if previous.get("jucator") in players else 0)
    else:
        player = None
    with st.form("guest_player_choice"):
        if not players:
            st.caption("Echipa aleasă nu are jucători în lot.")
        submit = st.form_submit_button("Salvează alegerea", type="primary", disabled=not bool(players))
    if submit and player:
        try:
            save_guest_selection(path, invitation, team, player)
            st.success("Alegerea ta a fost salvată.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    if previous:
        stats = data.get("echipe", {}).get(previous.get("echipa"), {}).get("jucatori", {}).get(previous.get("jucator"), {})
        if stats:
            st.metric("Goluri în această ligă", stats.get("goluri", 0))


def render_league_management(username, paths):
    accessible = get_user_leagues(username, include_hidden=True)
    users = load_users()
    account = users.get(username.casefold(), {})
    favorite_key = account.get("liga_preferata") if isinstance(account, dict) else None
    hidden_keys = set(account.get("ligii_ascunse", [])) if isinstance(account, dict) else set()
    st.subheader("Administrare ligi")
    st.caption("Alege liga preferată ca să apară prima sau elimină o ligă din lista acestui cont. Datele ligii rămân salvate.")
    if not accessible:
        st.info("Nu ai ligi în acest cont.")
        return
    pending_key = "confirm_delete_league"
    for entry in accessible:
        path = Path(entry["path"])
        league_key_value = league_key(entry)
        is_owner = entry.get("role") == "owner" and str(entry.get("owner", "")).casefold() == username.casefold()
        is_hidden = league_key_value in hidden_keys
        try:
            league_data = load_league(path)
            name = league_data.get("nume_liga", path.stem)
            teams = len(league_data.get("echipe", {}))
            matches = len(league_data.get("istoric_meciuri", []))
        except Exception as exc:
            name, teams, matches = path.stem, "?", "?"
            st.warning(f"Nu am putut încărca detaliile pentru liga «{name}»: {exc}")
        token = safe_slug(path.stem)
        with st.container(border=True):
            details, open_col, favorite_col, delete_col = st.columns([4.2, 1.1, 1.5, 1.1])
            star = " ⭐ Preferată" if league_key_value == favorite_key else ""
            details.markdown(f"### {name}{star}" + (" · Ascunsă" if is_hidden else ""))
            details.caption(f"{teams} echipe · {matches} meciuri · {'creată de tine' if is_owner else 'partajată'}")
            if not is_hidden and open_col.button("Deschide", key=f"manage_open_{token}", width="stretch"):
                st.session_state["entered_league"] = league_key_value
                st.session_state.pop("show_account_profile", None)
                st.rerun()
            if not is_hidden and favorite_col.button("Preferată" if league_key_value != favorite_key else "★ Preferată",
                                                      key=f"manage_favorite_{token}", width="stretch",
                                                      disabled=league_key_value == favorite_key):
                fresh_users = load_users()
                fresh_account = fresh_users.get(username.casefold())
                if fresh_account is not None:
                    fresh_account["liga_preferata"] = league_key_value
                    save_users(fresh_users)
                    st.success(f"«{name}» este acum liga ta preferată.")
                    st.rerun()
            button_label = "Afișează" if is_hidden else "Elimină"
            if delete_col.button(button_label, key=f"manage_delete_{token}", width="stretch"):
                st.session_state[pending_key] = league_key_value
                st.rerun()
            if st.session_state.get(pending_key) == league_key_value:
                st.warning((f"Afișezi din nou liga «{name}» în lista acestui cont?" if is_hidden else
                            f"Elimini liga «{name}» doar din lista acestui cont? Datele ei nu vor fi șterse."))
                confirm_col, cancel_col = st.columns(2)
                confirm_label = "Da, afișeaz-o" if is_hidden else "Da, elimin-o din listă"
                if confirm_col.button(confirm_label, type="primary", key=f"manage_confirm_{token}"):
                    try:
                        fresh_users = load_users()
                        fresh_account = fresh_users.get(username.casefold())
                        if fresh_account is None:
                            raise ValueError("Contul nu a fost găsit.")
                        current_hidden = set(fresh_account.get("ligii_ascunse", []))
                        if is_hidden:
                            current_hidden.discard(league_key_value)
                        else:
                            current_hidden.add(league_key_value)
                        fresh_account["ligii_ascunse"] = sorted(current_hidden)
                        if not is_hidden and fresh_account.get("liga_preferata") == league_key_value:
                            fresh_account.pop("liga_preferata", None)
                        save_users(fresh_users)
                        if not is_hidden and st.session_state.get("entered_league") == league_key_value:
                            st.session_state.pop("entered_league", None)
                        if not is_hidden and st.session_state.get("arbitraj_league_key") == league_key_value:
                            st.session_state.pop("arbitraj_league_key", None)
                            st.session_state.pop("arbitraj_fixture_id", None)
                        st.session_state.pop(pending_key, None)
                        st.success(f"Liga «{name}» a fost {'afișată din nou' if is_hidden else 'eliminată din listă'}. Datele au rămas salvate.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Liga nu a putut fi ștearsă: {exc}")
                if cancel_col.button("Anulează", key=f"manage_cancel_{token}"):
                    st.session_state.pop(pending_key, None)
                    st.rerun()


def render_player_dashboard(username, profile, paths):
    player_leagues = []
    for league_entry in paths:
        league_data = load_league(league_entry["path"])
        selection = (profile.get("selectii_ligi", {}).get(league_key(league_entry)) or
                     league_data.get("selectii_membri", {}).get(username, {}))
        team_name, player_name = selection.get("echipa"), selection.get("jucator")
        if not team_name or not player_name:
            continue
        if team_name not in league_data.get("echipe", {}):
            continue
        final_team, final_player = final_player_identity(league_data, team_name, player_name)
        stats = (league_data.get("echipe", {}).get(final_team, {}).get("jucatori", {}).get(final_player)
                 or league_data.get("echipe", {}).get(team_name, {}).get("jucatori", {}).get(player_name, {}))
        if not stats:
            continue
        league_name = league_data.get("nume_liga", Path(league_entry["path"]).stem)
        player_leagues.append({"entry": league_entry, "data": league_data, "league": league_name,
            "team": team_name, "player": player_name, "current_team": final_team,
            "current_player": final_player, "stats": stats,
            "motm": motm_wins_for_player(league_data, final_team, final_player)})

    st.subheader(tr("Jucătorul meu"))
    if not player_leagues:
        st.info("Asociază-ți un jucător în cel puțin o ligă din secțiunea de mai sus. Aici apar doar ligile în care ai ales un jucător.")
    else:
        player_tabs = st.tabs([tr("Statisticile mele"), tr("Meciuri jucate"), tr("Urmează"),
                               tr("Live"), tr("Trofee"), tr("Echipele mele")])
        totals = {key: 0 for key in STATS_JUCATOR}
        totals["omul_meciului"] = 0
        stats_rows, played_rows, upcoming_rows, live_rows, trophy_rows, team_rows = [], [], [], [], [], []
        for item in player_leagues:
            league_data, team_name, player_name = item["data"], item["team"], item["player"]
            league_name = item["league"]
            for field in STATS_JUCATOR:
                totals[field] += int(item["stats"].get(field, 0) or 0)
            totals["omul_meciului"] += item["motm"]
            player_trophies = trofee_jucator(league_data, item["current_team"], item["current_player"])
            team_trophies = trofee_echipa(league_data, item["current_team"])
            stats_rows.append({"Ligă": league_name, "Echipă": item["current_team"],
                "Jucător": item["current_player"], "Goluri": item["stats"].get("goluri", 0),
                "Assisturi": item["stats"].get("asisturi", 0),
                "Galbene": item["stats"].get("cartonase_galbene", 0),
                "Roșii": item["stats"].get("cartonase_rosii", 0), "Omul meciului": item["motm"]})
            for trophy in player_trophies:
                trophy_rows.append({"Trofeu": trophy, "Ligă": league_name,
                    "Echipă": item["current_team"], "Câștigat ca": item["current_player"]})
            for trophy in team_trophies:
                trophy_rows.append({"Trofeu": trophy, "Ligă": league_name,
                    "Echipă": item["current_team"], "Câștigat ca": "Membru al echipei"})

            match_records = [(match, "Liga") for match in league_data.get("istoric_meciuri", [])]
            for cup in league_data.get("cupe", []):
                for round_data in cup.get("runde", []):
                    for slot in round_data.get("meciuri", []):
                        for match in (slot.get("meci"), slot.get("meci_retur")):
                            if match:
                                match_records.append((match, cup.get("nume", "Cupă")))
            seen_matches = set()
            player_teams = {team_name, item["current_team"]}
            transfer_team, transfer_player = team_name, player_name
            for transfer in league_data.get("transferuri", []):
                if (transfer.get("de_la") == transfer_team and
                        str(transfer.get("jucator", "")).casefold() == transfer_player.casefold()):
                    player_teams.add(transfer.get("la"))
                    transfer_team = transfer.get("la")
                    transfer_player = transfer.get("nume_nou", transfer_player)
            for match, competition in match_records:
                if not player_teams.intersection((match.get("e1"), match.get("e2"))):
                    continue
                match_id = str(match.get("id") or id(match))
                if match_id in seen_matches:
                    continue
                seen_matches.add(match_id)
                played_rows.append({"Ligă": league_name, "Competiție": competition,
                    "Etapa": match.get("etapa") or "—",
                    "Meci": f"{match.get('e1')} {match.get('goluri_e1', 0)}–{match.get('goluri_e2', 0)} {match.get('e2')}"})

            for fixture in pending_fixtures(league_data):
                if item["current_team"] not in (fixture.get("e1"), fixture.get("e2")):
                    continue
                phase = fixture.get("arbitraj_live", {}).get("faza", "programat")
                row = {"Ligă": league_name, "Etapa": fixture.get("etapa") or "—",
                       "Competiție": "Liga", "Data": fixture.get("data") or "Nesetată",
                       "Meci": f"{fixture.get('e1')} – {fixture.get('e2')}"}
                if phase not in {"programat", "final"}:
                    live = fixture.get("arbitraj_live", {})
                    score_home, score_away = _live_match_score(league_data, fixture, live)
                    row["Scor live"] = f"{score_home}–{score_away}"
                    row["Stare"] = live.get("faza", "În desfășurare")
                    live_rows.append({"Ligă": league_name, **row})
                else:
                    upcoming_rows.append(row)

            for cup in league_data.get("cupe", []):
                if cup.get("castigatoare"):
                    continue
                for round_data in cup.get("runde", []):
                    for slot in round_data.get("meciuri", []):
                        if slot.get("castigator"):
                            continue
                        if item["current_team"] not in (slot.get("e1"), slot.get("e2")):
                            continue
                        if slot.get("meci") is None:
                            pending_leg = "Tur" if cup.get("tur_retur") else ""
                        elif cup.get("tur_retur") and slot.get("meci_retur") is None:
                            pending_leg = "Retur"
                        else:
                            continue
                        upcoming_rows.append({"Ligă": league_name,
                            "Competiție": (cup.get("nume", "Cupă") + (f" · {pending_leg}" if pending_leg else "")),
                            "Etapa": round_data.get("nume", "—"),
                            "Data": "Nesetată", "Meci": f"{slot.get('e1')} – {slot.get('e2')}"})

            team_rows.append({"Ligă": league_name, "Echipă aleasă": team_name,
                              "Jucător ales": player_name, "Echipă actuală după transferuri": item["current_team"]})
            current_team, current_player = team_name, player_name
            for transfer in league_data.get("transferuri", []):
                if (transfer.get("de_la") == current_team and
                        str(transfer.get("jucator", "")).casefold() == current_player.casefold()):
                    team_rows.append({"Ligă": league_name, "Echipă aleasă": transfer.get("de_la"),
                        "Jucător ales": transfer.get("jucator"), "Echipă actuală după transferuri": transfer.get("la")})
                    current_team, current_player = transfer.get("la"), transfer.get("nume_nou", current_player)

        with player_tabs[0]:
            metric_cols = st.columns(5)
            for col, label, field in zip(metric_cols,
                (tr("Goluri"), tr("Assisturi"), tr("Cartonașe galbene"), tr("Cartonașe roșii"), tr("Omul meciului")),
                ("goluri", "asisturi", "cartonase_galbene", "cartonase_rosii", "omul_meciului")):
                col.metric(label, totals[field])
            st.markdown(f"#### {tr('Pe fiecare ligă')}")
            render_cards(stats_rows)
        with player_tabs[1]:
            render_cards(played_rows)
        with player_tabs[2]:
            render_cards(upcoming_rows)
        with player_tabs[3]:
            render_cards(live_rows)
        with player_tabs[4]:
            if trophy_rows:
                st.metric(tr("Trofee câștigate"), len(trophy_rows))
                render_cards(trophy_rows)
            else:
                st.info("Nu ai trofee câștigate în ligile asociate încă.")
        with player_tabs[5]:
            render_cards(team_rows)




def render_account_profile(username, profile, paths, player_only=False):
    if player_only:
        st.title(tr("Jucătorul meu"))
        render_player_dashboard(username, profile, paths)
        return
    st.title(tr("Profilul meu"))
    st.caption(tr("Profilul rămâne disponibil indiferent de liga deschisă."))
    render_league_management(username, paths)

    today = dt.date.today()
    default_birthday = today.replace(year=today.year - 12)
    birthday_value = default_birthday
    try:
        birthday_value = dt.datetime.strptime(profile.get("data_nasterii", ""), "%d.%m.%Y").date()
    except (ValueError, TypeError):
        pass
    with st.expander(tr("Datele contului"), expanded=False):
        with st.form("global_profile_details"):
            display_name = st.text_input(tr("Nume și prenume"), value=profile.get("nume", username))
            account_email = st.text_input(tr("Adresă de e-mail"), value=profile.get("email", ""),
                                          help="Te poți conecta și cu această adresă după salvare.")
            birthday = st.date_input("Data nașterii", value=min(birthday_value, today),
                                     min_value=dt.date(1900, 1, 1), max_value=today)
            professional = st.selectbox(tr("Joci la un club profesionist?"), ["Da", "Nu"], format_func=tr,
                index=0 if profile.get("joaca_fotbal") == "Da" else 1)
            positions = list(POZITII_FOTBAL)
            position = st.selectbox(tr("Poziția ta"), positions, format_func=tr,
                index=positions.index(profile["pozitie"]) if profile.get("pozitie") in positions else 0)
            save_profile = st.form_submit_button(tr("Salvează profilul"))
        if save_profile:
            users = load_users()
            normalized_email = account_email.strip().casefold()
            email_in_use = any(user_key != username and
                str(user_record.get("email", "")).strip().casefold() == normalized_email
                for user_key, user_record in users.items()) if normalized_email else False
            if normalized_email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized_email):
                st.error("Introdu o adresă de e-mail validă.")
            elif email_in_use:
                st.error("Adresa aceasta este deja folosită de alt cont.")
            else:
                users[username].update({"nume": display_name.strip() or username,
                    "email": normalized_email, "data_nasterii": birthday.strftime("%d.%m.%Y"),
                    "joaca_fotbal": professional, "pozitie": position})
                save_users(users)
                st.success("Profilul a fost salvat.")
                st.rerun()

    with st.expander(tr("Schimbă parola"), expanded=False):
        with st.form("global_change_account_password"):
            old_password = st.text_input("Parola curentă", type="password")
            new_password = st.text_input("Parola nouă", type="password")
            new_password_confirm = st.text_input("Confirmă parola nouă", type="password")
            change_password = st.form_submit_button("Schimbă parola")
        if change_password:
            if not verify_password(profile, old_password):
                st.error("Parola curentă este greșită.")
            elif len(new_password) < 6:
                st.error("Parola nouă trebuie să aibă cel puțin 6 caractere.")
            elif new_password != new_password_confirm:
                st.error("Parolele noi nu coincid.")
            else:
                users = load_users()
                salt, digest = password_hash(new_password)
                users[username].update({"sare": salt, "hash": digest,
                    "iteratii": PASSWORD_ITERATIONS, "dispozitive": []})
                save_users(users)
                st.success("Parola a fost schimbată.")
                st.rerun()

    st.subheader(tr("Asocierea cu jucătorii din ligile tale"))
    if paths:
        league_labels = [f"{load_league(item['path']).get('nume_liga', item['path'].stem)} · @{item['owner']}"
                         for item in paths]
        selected_index = st.selectbox("Liga", range(len(paths)),
            format_func=lambda index: league_labels[index], key="global_profile_league_index")
        selected_entry = paths[selected_index]
        selected_data = load_league(selected_entry["path"])
        teams = list(selected_data.get("echipe", {}))
        if teams:
            selected_key = league_key(selected_entry)
            previous = (profile.get("selectii_ligi", {}).get(selected_key) or
                        selected_data.get("selectii_membri", {}).get(username, {}))
            widget_id = f"{safe_slug(selected_entry['owner'])}_{safe_slug(selected_entry['path'].stem)}"
            team = st.selectbox("Echipa", teams,
                index=teams.index(previous["echipa"]) if previous.get("echipa") in teams else 0,
                key=f"global_profile_team_{widget_id}")
            players = list(selected_data["echipe"][team].get("jucatori", {}))
            player = st.selectbox("Jucător", players,
                index=players.index(previous["jucator"]) if previous.get("jucator") in players else 0,
                key=f"global_profile_player_{widget_id}_{safe_slug(team)}") if players else None
            if not players:
                st.info("Echipa aleasă nu are încă jucători în lot.")
            if st.button("Salvează asocierea", type="primary", disabled=not bool(players),
                         key=f"global_profile_save_{widget_id}") and player:
                try:
                    if selected_entry["role"] == "owner":
                        users = load_users()
                        users[username].setdefault("selectii_ligi", {})[selected_key] = {
                            "echipa": team, "jucator": player, "pozitie": profile.get("pozitie", ""),
                            "actualizat": dt.datetime.now().timestamp()}
                        save_users(users)
                    else:
                        save_code_member_choice(selected_entry, username, team, player)
                    st.success("Asocierea a fost salvată.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Nu am putut salva asocierea: {exc}")
        else:
            st.info("Liga selectată nu are echipe încă.")
    else:
        st.info("Nu ai fost încă în nicio ligă. Când intri într-o ligă, ea va apărea aici.")

def auth_view(cookie_manager):
    st.session_state.setdefault("ui_language", "ro")
    render_language_selector(key="auth_language_selector_v2")
    st.markdown(f"## {tr('Intră în cont sau creează un profil')}")
    st.caption(tr("Te poți conecta cu numele de utilizator sau adresa de e-mail asociată contului."))
    if not SUPABASE_ENABLED:
        st.warning("Baza de date online nu este conectată. Conturile create aici se pot pierde când aplicația repornește. Verifică Secrets în setările Streamlit Cloud.")
    pending = st.session_state.get("pending_remember_login")
    if pending:
        st.info("Se salvează conectarea pe acest dispozitiv. Te vei conecta imediat ce browserul confirmă salvarea.")
        if st.button("Reîncearcă salvarea conectării", type="primary"):
            remember_account(cookie_manager, pending["username"])
        return
    login_tab, signup_tab = st.tabs([tr("Autentificare"), tr("Cont nou")])
    with login_tab:
        with st.form("login_account"):
            username = st.text_input(tr("Nume de utilizator sau e-mail"))
            password = st.text_input(tr("Parolă"), type="password")
            remember = st.checkbox(tr("Rămâi conectat pe acest dispozitiv (30 de zile)"), value=True)
            login = st.form_submit_button(tr("Intră în cont"), type="primary")
        if login:
            attempts = st.session_state.setdefault("login_attempts", [])
            now = dt.datetime.now().timestamp()
            attempts[:] = [item for item in attempts if now - item < 60]
            if len(attempts) >= 5:
                st.error("Prea multe încercări. Așteaptă un minut și încearcă din nou.")
            else:
                identifier = username.strip().casefold()
                try:
                    users = load_users()
                    if "@" in identifier:
                        key = next((user_key for user_key, user_record in users.items()
                                    if str(user_record.get("email", "")).strip().casefold() == identifier), "")
                    else:
                        key = identifier
                    record = users.get(key)
                except Exception as exc:
                    st.error("Nu pot accesa baza de date a conturilor. Verifică setările Supabase din Streamlit Cloud și încearcă din nou.")
                    st.caption(f"Detaliu: {exc}")
                    record = None
                    attempts.append(now)
                    st.stop()
                if record and verify_password(record, password):
                    st.session_state.pop("login_attempts", None)
                    st.session_state["ui_language"] = record.get("limba", "ro")
                    if remember:
                        remember_account(cookie_manager, key)
                        st.success("Conectarea se salvează pe acest dispozitiv…")
                        return
                    else:
                        revoke_remembered_account(cookie_manager)
                        st.session_state["user_key"] = key
                    st.session_state.pop("entered_league", None)
                    st.session_state.pop("active_league_picker", None)
                    st.rerun()
                attempts.append(now)
                st.error("E-mailul/numele de utilizator sau parola nu corespund. Dacă acest cont a fost creat înainte să adaugi e-mailul, conectează-te cu numele de utilizator.")
    with signup_tab:
        with st.form("signup_account"):
            username = st.text_input(tr("Nume de utilizator"), key="new_username")
            email = st.text_input(tr("Adresă de e-mail"), key="new_email")
            name = st.text_input(tr("Nume și prenume"))
            today = dt.date.today()
            birthday = st.date_input("Data nașterii", value=today.replace(year=today.year - 12),
                                     min_value=dt.date(1900, 1, 1), max_value=today)
            plays = st.selectbox("Joci la un club profesionist?", ["Da", "Nu"])
            position = st.selectbox("Poziția ta", list(POZITII_FOTBAL))
            password = st.text_input("Parolă (minimum 6 caractere)", type="password", key="new_password")
            confirm = st.text_input("Confirmă parola", type="password")
            remember_new = st.checkbox(tr("Rămâi conectat pe acest dispozitiv (30 de zile)"), value=True,
                                       key="remember_new_account")
            signup = st.form_submit_button("Creează cont", type="primary")
        if signup:
            if password != confirm:
                st.error("Parolele nu coincid.")
            else:
                try:
                    account_key = create_account(
                        username, email, password, name, birthday, plays, position)
                    users = load_users()
                    users[account_key]["limba"] = st.session_state.get("ui_language", "ro")
                    save_users(users)
                    st.session_state["ui_language"] = users[account_key]["limba"]
                    if remember_new:
                        remember_account(cookie_manager, account_key)
                        st.success("Contul a fost creat. Se salvează conectarea pe acest dispozitiv…")
                        return
                    st.session_state["user_key"] = account_key
                    st.session_state.pop("entered_league", None)
                    st.session_state.pop("active_league_picker", None)
                    st.success("Contul a fost creat.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error("Contul nu a putut fi salvat în baza de date. Verifică setările Supabase din Streamlit Cloud.")
                    st.caption(f"Detaliu: {exc}")


def main():
    st.set_page_config(page_title="Liga de fotbal", page_icon="⚽", layout="wide",
                       initial_sidebar_state="auto")
    install_ui_translations()
    cookie_manager = stx.CookieManager(key="persistent_cookie_manager")
    # Tema este fixată pe întunecat pentru a evita diferențele de contrast
    # dintre componentele Streamlit și stilurile personalizate.
    st.session_state["dark_mode"] = True
    if not st.session_state.get("user_key"):
        if not finish_pending_remember_login(cookie_manager):
            restore_remembered_account(cookie_manager)
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
    :root { color-scheme:light; --bg:#f5f7f3; --paper:#fff; --panel:#fff; --panel2:#edf3ed; --line:#e2e9e1;
            --text:#202a22; --muted:#718074; --green:#276747; --green-dark:#1e5238;
            --pale:#e9f2eb; --gold:#b17b2d; --sidebar:#eef2ec; --hover:#e1eae1;
            --selected:#dfece1; --input:#fcfdfb; --input-line:#dbe4da; --focus:#e5f0e7;
            --disabled:#e4e9e4; --disabled-text:#68736b; --header:rgba(245,247,243,.9);
            --shadow:0 8px 28px rgba(33,55,38,.055); }
    html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
    [data-testid="stAppViewContainer"] { background:var(--bg); color:var(--text); }
    [data-testid="stHeader"] { background:var(--header); }
    [data-testid="stMainBlockContainer"] { max-width:1440px; padding-top:2rem; padding-bottom:4rem; }
    [data-testid="stSidebar"] { background:var(--sidebar); border-right:1px solid var(--line); }
    [data-testid="stSidebar"] * { color:var(--text); }
    @media (max-width: 700px) {
        [data-testid="stSidebar"] {
            width: min(16rem, 65vw) !important;
            min-width: min(16rem, 65vw) !important;
            max-width: 65vw !important;
        }
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label { padding:9px 11px; border-radius:10px; transition:.15s ease; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background:var(--hover); }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) { background:var(--selected); color:var(--green-dark); font-weight:700; }
    [class*="st-key-spectator_match_picker"] [role="radiogroup"],
    [class*="st-key-spectator_motm_picker"] [role="radiogroup"],
    [class*="st-key-spectator_award_picker"] [role="radiogroup"],
    [class*="st-key-spectator_profile_"] [role="radiogroup"],
    [class*="st-key-spectator_invite_"] [role="radiogroup"],
    [class*="st-key-spectator_legacy_"] [role="radiogroup"] {
        max-height: 190px; overflow-y: auto; overscroll-behavior: contain;
    }
    h1,h2,h3 { font-family:'Manrope',sans-serif !important; letter-spacing:-.035em; color:var(--text); }
    h1 { font-weight:800 !important; }
    h2,h3 { font-weight:750 !important; }
    p, [data-testid="stCaptionContainer"] { color:var(--muted); }
    [data-testid="stMetric"] { background:var(--paper); border:1px solid var(--line);
        padding:17px 19px; border-radius:15px; box-shadow:var(--shadow); }
    .league-table-wrap { width:100%; overflow-x:auto; border:1px solid var(--line);
        border-radius:10px; background:var(--paper); box-shadow:var(--shadow); margin:.35rem 0 1rem; }
    table.league-table { width:100%; border-collapse:collapse; color:var(--text); font-size:.92rem; }
    .league-table th { background:var(--panel2); color:var(--muted); font-size:.76rem;
        font-weight:750; letter-spacing:.035em; text-align:left; white-space:nowrap;
        padding:10px 14px; border-bottom:1px solid var(--line); }
    .league-table td { padding:9px 14px; border-bottom:1px solid var(--line);
        white-space:nowrap; }
    .league-table tbody tr:nth-child(even) { background:var(--panel2); }
    .league-table tbody tr:last-child td { border-bottom:0; }
    .league-table tbody tr:hover { background:var(--pale); }
    [data-testid="stMetricLabel"] { color:var(--muted); font-size:.82rem; }
    [data-testid="stMetricValue"] { color:var(--green-dark); font-family:'Manrope',sans-serif; font-weight:800; }
    [data-baseweb="tab-list"] { gap:5px; border-bottom:1px solid var(--line);
        flex-wrap:wrap !important; overflow:visible !important; white-space:normal !important; }
    [data-baseweb="tab"] { background:transparent; border-radius:9px 9px 0 0;
        padding:9px 13px; color:var(--muted); font-weight:600; }
    [data-baseweb="tab"][aria-selected="true"], .stTabs [aria-selected="true"] { color:var(--green) !important; }
    [data-baseweb="tab-highlight"] { background-color:var(--green) !important; height:3px; }
    [data-testid="stForm"], [data-testid="stExpander"] { border:1px solid var(--line); border-radius:14px; background:var(--paper); }
    [data-testid="stVerticalBlockBorderWrapper"] > div { border-color:var(--line) !important; border-radius:16px !important; background:var(--paper); box-shadow:var(--shadow); }
    [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input, [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div { border-color:var(--input-line); border-radius:9px; background:var(--input); color:var(--text); }
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div { background:var(--input) !important; color:var(--text) !important; }
    [data-testid="stTextInput"] input:focus, [data-testid="stNumberInput"] input:focus { border-color:#78a68a; box-shadow:0 0 0 3px var(--focus); }
    [data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"] { background:var(--paper) !important; color:var(--text) !important; }
    [role="option"] { color:var(--text) !important; }
    [role="option"]:hover, [aria-selected="true"][role="option"] { background:var(--panel2) !important; color:var(--text) !important; }
    [data-testid="stWidgetLabel"], [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] * { color:var(--text); }
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * { color:var(--muted); }
    a { color:var(--green) !important; }
    [data-testid="stAlert"] { color:var(--text); }
    [data-testid="stRadio"] label, [data-testid="stCheckbox"] label,
    [data-testid="stToggle"] label { color:var(--text) !important; }
    div.stButton > button, div.stFormSubmitButton > button { border-radius:9px;
        border:1px solid #dce5dc; min-height:42px; font-weight:700; transition:.15s ease; }
    div.stButton > button:hover, div.stFormSubmitButton > button:hover { border-color:#8aaf96; color:var(--green-dark); transform:translateY(-1px); }
    div.stButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"] {
        background:var(--green); border-color:var(--green); color:#fff; box-shadow:0 4px 12px #27674722; }
    div.stButton > button[kind="primary"]:hover, div.stFormSubmitButton > button[kind="primary"]:hover { background:var(--green-dark); color:#fff; }
    button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"] {
        background:var(--green) !important; border-color:var(--green) !important; color:#fff !important;
        opacity:1 !important; box-shadow:0 4px 12px #27674722 !important; }
    button[data-testid="stBaseButton-primary"] *, button[data-testid="stBaseButton-primaryFormSubmit"] * {
        color:#fff !important; opacity:1 !important; font-weight:750 !important; }
    button[data-testid="stBaseButton-primary"]:hover, button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
        background:var(--green-dark) !important; border-color:var(--green-dark) !important; color:#fff !important; }
    button[data-testid="stBaseButton-primary"]:disabled, button[data-testid="stBaseButton-primaryFormSubmit"]:disabled {
        background:var(--disabled) !important; border-color:var(--line) !important; color:var(--disabled-text) !important;
        box-shadow:none !important; opacity:1 !important; cursor:not-allowed !important; }
    button[data-testid="stBaseButton-primary"]:disabled *, button[data-testid="stBaseButton-primaryFormSubmit"]:disabled * {
        color:var(--disabled-text) !important; }
    button[data-testid="stBaseButton-secondary"] { color:var(--text) !important; }
    button[data-testid="stBaseButton-secondary"] * { color:inherit !important; }
    button[data-testid^="stBaseButton-"]:focus-visible { outline:3px solid #83bd94 !important; outline-offset:2px; }
    [data-testid="stAlert"] { border-radius:12px; }
    [data-testid="stFileUploader"] section { border-radius:12px; border-color:var(--input-line); background:var(--input); color:var(--text); }
    .league-kicker { color:var(--green); text-transform:uppercase; letter-spacing:.14em;
        font-size:.74rem; font-weight:800; margin-bottom:.2rem; }
    .league-subtitle { color:var(--muted); margin-top:-.35rem; margin-bottom:1.5rem; font-size:1.03rem; }
    .bike-ad-wrap { margin:0 0 1.15rem; }
    a.bike-ad-banner { display:flex; align-items:center; justify-content:space-between; gap:1rem;
        padding:1rem 1.25rem; border-radius:16px; border:1px solid #3a5945;
        background:linear-gradient(105deg,#17281f 0%,#203b2b 58%,#284b35 100%);
        color:#f5fff7 !important; text-decoration:none !important; box-shadow:0 9px 25px rgba(0,0,0,.18);
        transition:transform .16s ease, box-shadow .16s ease, border-color .16s ease; }
    a.bike-ad-banner:hover { transform:translateY(-2px); border-color:#71b984;
        box-shadow:0 13px 30px rgba(0,0,0,.24); }
    .bike-ad-left { display:flex; align-items:center; gap:1rem; min-width:0; }
    .bike-ad-icon { display:grid; place-items:center; flex:0 0 3.25rem; height:3.25rem;
        border-radius:13px; background:#d9f2df; color:#17442a !important; font-size:1.8rem; }
    .bike-ad-copy { min-width:0; }
    .bike-ad-eyebrow { display:block; color:#a8d8b4 !important; text-transform:uppercase;
        letter-spacing:.12em; font-size:.67rem; font-weight:800; margin-bottom:.16rem; }
    .bike-ad-title { display:block; color:#fff !important; font:800 1.15rem 'Manrope',sans-serif;
        line-height:1.25; }
    .bike-ad-subtitle { display:block; color:#d0e2d4 !important; font-size:.87rem; margin-top:.15rem; }
    .bike-ad-cta { flex:0 0 auto; display:inline-flex; align-items:center; gap:.4rem;
        border-radius:10px; background:#d9f2df; color:#17442a !important; font-weight:800;
        padding:.72rem .95rem; white-space:nowrap; }
    .bike-ad-cta::after { content:'↗'; font-size:1.05rem; }
    @media(max-width:700px) { [data-testid="stMainBlockContainer"] { padding:1.2rem 1rem 3rem; }
        [data-testid="stMetric"] { padding:13px; } h1 { font-size:1.8rem !important; }
        a.bike-ad-banner { padding:.8rem; gap:.65rem; border-radius:13px; }
        .bike-ad-left { gap:.65rem; }
        .bike-ad-icon { flex-basis:2.7rem; height:2.7rem; font-size:1.5rem; }
        .bike-ad-title { font-size:.96rem; }
        .bike-ad-subtitle { font-size:.76rem; }
        .bike-ad-cta { padding:.62rem .7rem; font-size:.78rem; } }
    </style>
    """, unsafe_allow_html=True)
    dark_mode = bool(st.session_state.get("dark_mode", False))
    if dark_mode:
        st.markdown("""
        <style>
        :root { color-scheme:dark; --bg:#111815 !important; --paper:#1b2520 !important;
          --panel:#1b2520 !important; --panel2:#24322a !important; --line:#34443a !important;
          --text:#e8f0e9 !important; --muted:#a5b4a8 !important; --green:#56b878 !important;
          --green-dark:#328c54 !important; --pale:#203a2a !important; --gold:#e5b86b !important;
          --sidebar:#17211b !important; --hover:#24322a !important; --selected:#203a2a !important;
          --input:#131c17 !important; --input-line:#46574b !important; --focus:#203a2a !important;
          --disabled:#303b34 !important; --disabled-text:#b7c3ba !important;
          --header:rgba(17,24,21,.94) !important;
          --shadow:0 10px 30px rgba(0,0,0,.2) !important; }
        [data-testid="stAppViewContainer"] { background:#111815 !important; color:#e8f0e9 !important; }
        [data-testid="stHeader"] { background:var(--header) !important; }
        [data-testid="stSidebar"] { background:#17211b !important; border-color:#34443a !important; }
        [data-testid="stSidebar"] *, h1,h2,h3,[data-testid="stMarkdownContainer"],
        [data-testid="stMarkdownContainer"] *,[data-testid="stWidgetLabel"] { color:#e8f0e9; }
        p,[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] * { color:#a5b4a8 !important; }
        [data-testid="stMetric"],[data-testid="stForm"],[data-testid="stExpander"],
        [data-testid="stVerticalBlockBorderWrapper"] > div { background:#1b2520 !important;
          border-color:#34443a !important; color:#e8f0e9 !important; }
        [data-testid="stMetricValue"] { color:#82d39c !important; }
        a { color:#82d39c !important; }
        [data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,[data-testid="stDateInput"] input,
        [data-testid="stTextArea"] textarea,[data-testid="stSelectbox"] [data-baseweb="select"] > div,
        [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
          background:#131c17 !important; color:#e8f0e9 !important; border-color:#46574b !important; }
        [data-testid="stTextInputRootElement"] { background:#131c17 !important; border-color:#46574b !important; }
        [data-testid="stTextInput"] input::placeholder,[data-testid="stTextArea"] textarea::placeholder { color:#8c9c90 !important; }
        button[aria-label="Show password"] { background:#24322a !important; color:#e8f0e9 !important; border-color:#46574b !important; }
        button[aria-label="Show password"] * { color:#e8f0e9 !important; }
        [data-baseweb="tab"] { color:#a5b4a8 !important; }
        [data-baseweb="tab"][aria-selected="true"] { color:#82d39c !important; }
        [data-testid="stFileUploader"] section { background:#17211b !important; border-color:#46574b !important; }
        [data-baseweb="popover"],[data-baseweb="menu"],[role="listbox"] { background:#1b2520 !important; color:#e8f0e9 !important; }
        [role="option"] { color:#e8f0e9 !important; }
        [role="option"]:hover,[aria-selected="true"][role="option"] { background:#24322a !important; color:#fff !important; }
        [data-testid="stAlert"] { background:#1b2520 !important; }
        button[data-testid="stBaseButton-secondary"] { background:#202d25 !important; color:#e8f0e9 !important; border-color:#405246 !important; }
        button[data-testid="stBaseButton-secondary"] * { color:#e8f0e9 !important; }
        button[data-testid="stBaseButton-primary"],button[data-testid="stBaseButton-primaryFormSubmit"] {
          background:#2f9b5b !important; border-color:#2f9b5b !important; color:#fff !important; }
        button[data-testid="stBaseButton-primary"] *,button[data-testid="stBaseButton-primaryFormSubmit"] * { color:#fff !important; }
        button[data-testid="stBaseButton-primary"]:disabled,button[data-testid="stBaseButton-primaryFormSubmit"]:disabled {
          background:#303b34 !important; border-color:#3d4941 !important; color:#9eaaa1 !important; }
        button[data-testid="stBaseButton-primary"]:disabled *,button[data-testid="stBaseButton-primaryFormSubmit"]:disabled * { color:#9eaaa1 !important; }
        </style>
        """, unsafe_allow_html=True)
    st.markdown('''
    <div class="bike-ad-wrap">
      <a class="bike-ad-banner" href="https://event.2performant.com/events/click?ad_type=quicklink&amp;aff_code=7067ba403&amp;unique=6e0b0b0df&amp;redirect_to=https%3A%2F%2Fpiese-biciclete.eu%2F" target="_blank" rel="sponsored noopener noreferrer" aria-label="Vizitează magazinul Piese-Biciclete.eu — link afiliat">
        <span class="bike-ad-left">
          <span class="bike-ad-icon" aria-hidden="true">🚲</span>
          <span class="bike-ad-copy">
            <span class="bike-ad-eyebrow">Partener · link afiliat</span>
            <span class="bike-ad-title">Piese-Biciclete.eu</span>
            <span class="bike-ad-subtitle">Biciclete, piese și accesorii pentru următoarea ta aventură</span>
          </span>
        </span>
        <span class="bike-ad-cta">Descoperă magazinul</span>
      </a>
    </div>
    ''', unsafe_allow_html=True)
    st.title(f"⚽ {tr('Managerul ligii de fotbal')}")
    st.markdown('<div class="league-subtitle">Clasamente, meciuri și cupe într-un singur loc</div>', unsafe_allow_html=True)
    access_code = str(st.query_params.get("cod", "")).strip()
    invite_token = str(st.query_params.get("invitat", "")).strip()
    guest_entry = find_access_code(access_code) if access_code else None
    if not access_code and invite_token:
        guest_entry = find_invitation(invite_token)
    if access_code and not guest_entry:
        st.error("Codul de acces nu este valid sau a fost schimbat.")
        if st.button("Înapoi la pagina principală"):
            st.query_params.clear()
            st.session_state.pop("active_guest_invite", None)
            st.session_state.pop("active_guest_access", None)
            st.rerun()
        return
    if invite_token and not guest_entry:
        st.error("Această invitație nu mai este valabilă sau a fost revocată.")
        if st.button("Înapoi la pagina principală"):
            st.query_params.clear()
            st.session_state.pop("active_guest_invite", None)
            st.session_state.pop("active_guest_access", None)
            st.rerun()
        return
    is_code_access = bool(guest_entry and guest_entry.get("access_method") == "cod")
    is_legacy_guest = bool(guest_entry and guest_entry.get("access_method") == "legacy")
    is_guest = is_legacy_guest
    username = st.session_state.get("user_key")
    users = load_users()
    if is_code_access and (not username or username not in users):
        auth_view(cookie_manager)
        return
    if not is_guest and not is_code_access and (not username or username not in users):
        st.session_state.pop("user_key", None)
        st.session_state.pop("active_guest_invite", None)
        st.session_state.pop("active_guest_access", None)
        auth_view(cookie_manager)
        return
    guest_profile = None
    if is_code_access:
        profile = users[username]
        profile.setdefault("selectii_ligi", {})
        try:
            access_role = join_league_with_code(guest_entry, username, access_code)
        except ValueError as exc:
            st.error(str(exc))
            if st.button("Înapoi la ligile mele"):
                st.query_params.clear()
                st.session_state.pop("spectator_profile", None)
                st.session_state.pop("spectator_choice_stage", None)
                st.rerun()
            return
        except Exception as exc:
            st.error("Nu am putut salva intrarea ca jucător. Verifică dacă aplicația Streamlit Cloud este actualizată și încearcă din nou.")
            st.caption(f"Detaliu: {exc}")
            if st.button("Reîncearcă intrarea"):
                st.rerun()
            return
        if access_role != "owner":
            st.session_state["entered_league"] = league_key(guest_entry)
        else:
            st.session_state["entered_league"] = league_key(guest_entry)
        st.query_params.clear()
        st.session_state.pop("spectator_profile", None)
        st.session_state.pop("spectator_choice_stage", None)
        st.session_state.pop("spectator_team_choice", None)
        st.session_state.pop("spectator_player_choice", None)
        st.rerun()
        return
    if is_guest:
        invite = guest_entry["invitation"]
        profile = {"nume": invite.get("nume", "Invitat"), "pozitie": "", "selectii_ligi": {}}
        st.session_state.pop("active_guest_access", None)
        st.session_state["active_guest_invite"] = {
            "path": str(guest_entry["path"]), "token": invite_token, "id": invite.get("id")}
        paths = [guest_entry]
    else:
        st.session_state.pop("active_guest_invite", None)
        st.session_state.pop("active_guest_access", None)
        profile = users[username]
        profile.setdefault("selectii_ligi", {})
        paths = get_user_leagues(username)
        st.session_state.setdefault("ui_language", profile.get("limba", "ro"))
    st.session_state.setdefault("login_attempts", [])
    st.session_state["active_league_role"] = "owner"
    with st.sidebar:
        if is_guest:
            st.markdown(f"### 🎟️ {profile['nume']}")
            st.caption("Cod de ligă · acces temporar" if guest_entry.get("access_method") == "cod"
                       else "Invitație de ligă · acces temporar")
            if st.button("Ieși din invitație", width="stretch"):
                st.query_params.clear()
                st.session_state.pop("active_guest_invite", None)
                st.session_state.pop("active_guest_access", None)
                st.session_state.pop("spectator_profile", None)
                st.session_state.pop("spectator_choice_stage", None)
                st.session_state.pop("spectator_team_choice", None)
                st.session_state.pop("spectator_player_choice", None)
                st.rerun()
        else:
            st.markdown(f"### 👤 {profile.get('nume') or username}")
            st.caption(f"@{username}")
            render_language_selector(username, key="sidebar_language_selector_v2")
            if st.button(f"👤 {tr('Profilul meu')}", width="stretch", key="open_global_profile"):
                st.session_state["show_account_profile"] = True
                st.session_state.pop("show_player_profile", None)
                st.rerun()
            if st.button(f"⚽ {tr('Jucătorul meu')}", width="stretch", key="open_player_profile"):
                st.session_state["show_account_profile"] = True
                st.session_state["show_player_profile"] = True
                st.rerun()
        st.divider()
    if st.session_state.get("show_account_profile") and not is_guest:
        if st.button(f"↩ {tr('Înapoi la aplicație')}"):
            st.session_state.pop("show_account_profile", None)
            st.session_state.pop("show_player_profile", None)
            st.rerun()
        render_account_profile(username, profile, paths,
                               player_only=bool(st.session_state.get("show_player_profile")))
        st.divider()
        if st.button(tr("Deconectare"), type="secondary", key="logout_from_profile"):
            revoke_remembered_account(cookie_manager)
            st.session_state.pop("user_key", None)
            st.session_state.pop("active_league_role", None)
            st.session_state.pop("entered_league", None)
            st.session_state.pop("active_league_picker", None)
            st.session_state.pop("show_account_profile", None)
            st.rerun()
        return
    by_label = {f"{load_league(item['path']).get('nume_liga', item['path'].stem)} · "
                f"{item['owner']} · {'proprie' if item['role'] == 'owner' else item['role']}": item
                for item in paths}
    by_key = {league_key(item): item for item in paths}
    entered_key = league_key(guest_entry) if is_guest else st.session_state.get("entered_league")
    if entered_key not in by_key:
        st.session_state.pop("entered_league", None)
        entered_key = None
    if entered_key is None:
        st.markdown(f"## {tr('Bine ai venit în Managerul Ligii de Fotbal')}")
        st.caption(tr("Creează o ligă nouă sau intră într-o ligă pe care o administrezi ori care ți-a fost partajată."))
        if not SUPABASE_ENABLED:
            st.warning("Supabase nu este conectat: ligile se salvează doar local și se pot pierde când aplicația repornește. Verifică SUPABASE_URL și SUPABASE_SERVICE_ROLE_KEY în Secrets.")
        with st.expander(f"⚙️ {tr('Administrează ligile mele')}", expanded=False):
            render_league_management(username, paths)
        enter_col, create_col = st.columns(2, gap="large")
        with create_col:
            with st.container(border=True):
                st.markdown(f"### ➕ {tr('Creează o ligă')}")
                with st.form("launcher_create_league"):
                    new_name = st.text_input(tr("Numele ligii"), "Liga mea")
                    source_entry = st.selectbox("Pornește de la", [None, *paths],
                        format_func=lambda item: tr("Ligă goală") if item is None else
                            f"{load_league(item['path']).get('nume_liga', item['path'].stem)} · @{item['owner']}")
                    league_type = st.selectbox(tr("Tipul competiției"), ["Ligă", "Ligă + cupă", "Cupă"], format_func=tr)
                    create = st.form_submit_button(tr("Creează liga"), type="primary", width="stretch")
                if create:
                    try:
                        created_path = create_user_league(username, new_name, source_entry, league_type)
                        saved_entry = next((item for item in get_user_leagues(username)
                            if item.get("role") == "owner" and item["path"] == created_path), None)
                        if not saved_entry:
                            raise ValueError("Liga a fost creată, dar nu apare încă în lista ligilor contului. Reîncarcă pagina și verifică dacă a fost salvată.")
                        st.session_state["entered_league"] = league_key(saved_entry)
                        st.session_state["active_league_role"] = "owner"
                        st.session_state.pop("active_league_picker", None)
                        st.rerun()
                    except Exception as exc:
                        st.error("Liga nu a putut fi creată și confirmată în stocare.")
                        st.caption(f"Detaliu: {exc}")
        with enter_col:
            with st.container(border=True):
                st.markdown(f"### 📂 {tr('Intră în ligă')}")
                if paths:
                    selected_launcher = st.selectbox(tr("Alege liga"), list(by_label), key="launcher_league")
                    selected_launcher_entry = by_label[selected_launcher]
                    st.caption(f"Proprietar: @{selected_launcher_entry['owner']} · Acces: "
                               f"{'propriu' if selected_launcher_entry['role'] == 'owner' else selected_launcher_entry['role']}")
                    if st.button(tr("Intră în ligă"), type="primary", width="stretch"):
                        st.session_state["entered_league"] = league_key(selected_launcher_entry)
                        st.session_state.pop("active_league_picker", None)
                        st.rerun()
                else:
                    st.info("Nu ai încă ligi. Creează una sau importă un fișier JSON.")
                first_import = st.file_uploader("Importă o ligă existentă", type=["json"], key="launcher_import")
                if first_import and st.button("Importă liga", key="launcher_import_button"):
                    try:
                        imported = normalizeaza_date(json.loads(first_import.getvalue().decode("utf-8")))
                        if SUPABASE_ENABLED:
                            existing_names = {load_league(item["path"]).get("nume_liga", "").casefold()
                                              for item in get_user_leagues(username) if item["role"] == "owner"}
                            target = db_league_path(username, uuid.uuid4())
                            already_exists = imported.get("nume_liga", "").casefold() in existing_names
                        else:
                            user_folder = BASE_DIR / username
                            user_folder.mkdir(parents=True, exist_ok=True)
                            target = user_folder / f"{safe_slug(imported['nume_liga'])}.json"
                            already_exists = target.exists()
                        if already_exists:
                            st.error("Există deja o ligă cu acest nume în cont.")
                        else:
                            save_league(target, imported)
                            st.session_state["entered_league"] = f"{username}/{target.name}"
                            st.session_state.pop("active_league_picker", None)
                            st.rerun()
                    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                        st.error(f"Fișierul nu este un JSON de ligă valid: {exc}")
                st.divider()
                st.markdown("#### Intră cu un cod de ligă")
                with st.form("launcher_access_code"):
                    access_code = st.text_input("Cod spectator sau editor")
                    enter_with_code = st.form_submit_button("Continuă cu codul", type="primary", width="stretch")
                if enter_with_code:
                    normalized_code = normalize_access_code(access_code)
                    if len(normalized_code) != 12:
                        st.error("Codul trebuie să aibă 12 caractere.")
                    else:
                        st.query_params["cod"] = normalized_code
                        st.rerun()
        return
    chosen_key = entered_key
    selected_entry = by_key[chosen_key]
    path = selected_entry["path"]
    role = selected_entry["role"]
    owner = selected_entry["owner"]
    st.session_state["active_league_role"] = role
    data = load_league(path)
    if role not in {"owner", "editor"}:
        st.title(data.get("nume_liga", "Liga"))
        st.caption(f"Partajată de @{owner}")
        render_view_only(data, username, profile, selected_entry,
                         guest_entry if guest_entry and guest_entry.get("access_method") == "legacy" else None,
                         guest_profile)
        if not is_guest:
            with st.sidebar:
                st.divider()
            if st.button(f"↩ {tr('Schimbă liga')}", width="stretch", key="change_league_viewer"):
                    st.session_state.pop("entered_league", None)
                    st.session_state.pop("active_league_picker", None)
                    st.rerun()
        return
    pages = ["Clasament", "Statistici", "Echipe și jucători", "Meciuri și program", "Arbitraj", "Cupa",
            "Supercupa", "Premii sezon", "Transferuri", "Membri", "Import / export", "Setări ligă"]
    if is_guest and guest_entry.get("access_method") == "legacy" and guest_entry["invitation"].get("tip") == "jucator":
        pages.insert(-1, "Alegerea mea")
    navigation_labels = {
        "Clasament": "🏆  Clasament",
        "Setări ligă": "⚙  Setări ligă",
        "Echipe și jucători": "🛡  Echipe și jucători",
        "Meciuri și program": "⚽  Meciuri și program",
        "Arbitraj": "⏱  Arbitraj",
        "Cupa": "🥇  Cupa",
        "Supercupa": "🏅  Supercupa",
        "Statistici": "📊  Statistici",
        "Premii sezon": "🏅  Premii sezon",
        "Transferuri": "🔁  Transferuri",
        "Membri": "👥  Membri",
        "Profil": "👤  Profil",
        "Alegerea mea": "🪪  Alegerea mea",
        "Import / export": "⚙  Import / export",
    }
    if st.session_state.get("main_navigation") not in pages:
        st.session_state["main_navigation"] = pages[0]
    page = st.sidebar.radio(tr("Navigare"), pages,
        format_func=lambda item: navigation_labels[item].replace(item, tr(item)), key="main_navigation")
    if not is_guest:
        with st.sidebar:
            st.divider()
            if st.button(f"↩ {tr('Schimbă liga')}", width="stretch", key="change_league_member"):
                st.session_state.pop("entered_league", None)
                st.session_state.pop("active_league_picker", None)
                st.rerun()

    if page == "Alegerea mea" and is_guest:
        render_guest_player_choice(data, path, guest_entry["invitation"])

    if page == "Arbitraj":
        render_owner_arbitration(data, path, league_key(selected_entry))
        return

    if page == "Clasament":
        st.subheader(data["nume_liga"])
        c1, c2, c3 = st.columns(3)
        c1.metric("Echipe", len(data["echipe"]))
        c2.metric("Meciuri", len(data["istoric_meciuri"]))
        c3.metric("Jucători", sum(len(t["jucatori"]) for t in data["echipe"].values()))
        if data["echipe"]:
            render_cards(ranking(data))
            st.caption("Forma ultimelor cinci meciuri: V = victorie · E = egal · Î = înfrângere")
        else:
            st.info("Adaugă echipe pentru a vedea clasamentul.")


    if page == "Setări ligă":
        st.subheader("Setări ligă")
        settings_widget_id = safe_slug(league_key(selected_entry))
        rename = st.text_input("Denumire", value=data["nume_liga"], key=f"rename_{settings_widget_id}")
        if st.button("Salvează denumirea") and rename.strip():
            data["nume_liga"] = rename.strip(); save_league(path, data); st.rerun()
        st.markdown("**Votul pentru omul meciului**")
        voting_modes = {
            "Spectatorii votează; jucătorii echipelor din meci nu votează": "no_players",
            "Toți pot vota; jucătorii nu se pot vota pe ei": "no_self_vote",
        }
        current_mode = data.get("setari_liga", {}).get("motm_voting_mode", "no_players")
        current_label = next((label for label, value in voting_modes.items()
                              if value == current_mode), next(iter(voting_modes)))
        selected_mode_label = st.selectbox(
            "Cine poate vota?", list(voting_modes), index=list(voting_modes).index(current_label),
            key=f"motm_voting_mode_select_{settings_widget_id}")
        if st.button("Salvează setările votului", key=f"save_motm_voting_settings_{settings_widget_id}"):
            data.setdefault("setari_liga", {})["motm_voting_mode"] = voting_modes[selected_mode_label]
            save_league(path, data)
            st.success("Setarea votului pentru omul meciului a fost salvată.")
            st.rerun()
        st.divider()
        st.markdown("**Premii de final de sezon**")
        award_modes = {"Alegere directă de către proprietar/editor": "direct",
                       "Vot cu punctaj pentru jucători": "vote"}
        current_award_mode = data.get("setari_liga", {}).get("award_voting_mode", "direct")
        current_award_label = next((label for label, value in award_modes.items()
                                    if value == current_award_mode), "Alegere directă de către proprietar/editor")
        selected_award_label = st.selectbox("Metoda de acordare a premiilor individuale",
            list(award_modes), index=list(award_modes).index(current_award_label),
            key=f"award_voting_mode_select_{settings_widget_id}")
        if st.button("Salvează metoda premiilor", key=f"save_award_voting_mode_{settings_widget_id}"):
            selected_mode = award_modes[selected_award_label]
            settings = data.setdefault("setari_liga", {})
            if selected_mode == "direct" and settings.get("award_voting_open"):
                settings["award_voting_open"] = False
                finalize_award_vote_results(data)
            elif selected_mode == "vote" and current_award_mode != "vote":
                for award in definitii_premii(data):
                    if award["tip"] == "jucator" and not award_is_automatic(award):
                        data.setdefault("premii_alese", {}).pop(award["cheie"], None)
            settings["award_voting_mode"] = selected_mode
            save_league(path, data)
            st.success("Metoda de acordare a premiilor a fost salvată.")
            st.rerun()
        if current_award_mode == "vote":
            if data.get("setari_liga", {}).get("award_voting_open"):
                st.success("Votul pentru premiile de sezon este deschis.")
                if st.button("Închide votul și calculează câștigătorii", key=f"close_award_voting_{settings_widget_id}"):
                    data.setdefault("setari_liga", {})["award_voting_open"] = False
                    finalize_award_vote_results(data)
                    save_league(path, data)
                    st.success("Votul a fost închis și punctajele au fost calculate.")
                    st.rerun()
            else:
                st.info("Votul este închis. Membrii ligii nu pot vota până nu îl activezi.")
                if st.button("Deschide votul pentru premii", type="primary", key=f"open_award_voting_{settings_widget_id}"):
                    data.setdefault("setari_liga", {})["award_voting_open"] = True
                    save_league(path, data)
                    st.success("Votul pentru premiile de sezon este deschis.")
                    st.rerun()
        st.divider()
        st.markdown("**Schimbări în meciuri**")
        substitution_rules = {
            "5 schimbări pe meci · cine iese nu mai intră": "5_no_return",
            "5 schimbări pe meci · cine iese mai poate intra": "5_return",
            "Schimbări nelimitate · cine iese nu mai intră": "unlimited_no_return",
            "Schimbări nelimitate · cine iese mai poate intra": "unlimited_return",
        }
        current_substitution_rule = data.get("setari_liga", {}).get("substitution_rule", "5_no_return")
        current_substitution_label = next((label for label, value in substitution_rules.items()
            if value == current_substitution_rule), next(iter(substitution_rules)))
        selected_substitution_label = st.selectbox("Regula schimbărilor", list(substitution_rules),
            index=list(substitution_rules).index(current_substitution_label),
            key=f"substitution_rule_{settings_widget_id}")
        st.caption("Limita de cinci schimbări se aplică separat fiecărei echipe și include prelungirile.")
        if st.button("Salvează regula schimbărilor", key=f"save_substitution_rule_{settings_widget_id}"):
            data.setdefault("setari_liga", {})["substitution_rule"] = substitution_rules[selected_substitution_label]
            save_league(path, data)
            st.success("Regula schimbărilor a fost salvată.")
            st.rerun()
        st.divider()
        st.markdown("**Formatul cupelor eliminatorii**")
        cup_leg_options = {"Un singur meci": "single", "Tur și retur": "home_away"}
        current_leg_format = data.get("setari_liga", {}).get("cup_leg_format", "single")
        selected_leg_label = st.selectbox("Format pentru cupele noi",
            list(cup_leg_options),
            index=list(cup_leg_options.values()).index(current_leg_format)
                if current_leg_format in cup_leg_options.values() else 0,
            key=f"cup_leg_format_select_{settings_widget_id}")
        current_super_leg = data.get("setari_liga", {}).get("supercup_leg_format", "single")
        selected_super_leg_label = st.selectbox("Format pentru Supercupele noi",
            list(cup_leg_options),
            index=list(cup_leg_options.values()).index(current_super_leg)
                if current_super_leg in cup_leg_options.values() else 0,
            key=f"supercup_leg_format_select_{settings_widget_id}")
        cup_tie_options = {"Direct la penaltyuri": "penalties",
                           "Două reprize de prelungiri, apoi penaltyuri dacă e egal": "extra_time"}
        current_cup_tie = data.get("setari_liga", {}).get("cup_tie_resolution", "penalties")
        selected_cup_tie = st.selectbox("Dacă egalitatea persistă în cupă",
            list(cup_tie_options),
            index=list(cup_tie_options.values()).index(current_cup_tie)
                if current_cup_tie in cup_tie_options.values() else 0,
            key=f"cup_tie_resolution_select_{settings_widget_id}")
        current_super_tie = data.get("setari_liga", {}).get("supercup_tie_resolution", "penalties")
        selected_super_tie = st.selectbox("Dacă finala Supercupei se termină egal",
            list(cup_tie_options),
            index=list(cup_tie_options.values()).index(current_super_tie)
                if current_super_tie in cup_tie_options.values() else 0,
            key=f"supercup_tie_resolution_select_{settings_widget_id}")
        st.caption("Formatele se aplică competițiilor noi. Pentru o cupă sau Supercupă existentă, formatul se poate schimba înainte de primul rezultat.")
        if st.button("Salvează setările cupelor", key=f"save_cup_settings_{settings_widget_id}"):
            settings = data.setdefault("setari_liga", {})
            settings["cup_leg_format"] = cup_leg_options[selected_leg_label]
            settings["supercup_leg_format"] = cup_leg_options[selected_super_leg_label]
            settings["cup_tie_resolution"] = cup_tie_options[selected_cup_tie]
            settings["supercup_tie_resolution"] = cup_tie_options[selected_super_tie]
            save_league(path, data)
            st.success("Setările cupelor și Supercupei au fost salvate.")
            st.rerun()

    if page == "Echipe și jucători":
        st.subheader("Echipe și loturi")
        with st.form("echipa_noua"):
            team_name = st.text_input("Adaugă echipă")
            add_team = st.form_submit_button("Adaugă")
        if add_team:
            if not team_name.strip(): st.error("Introdu numele echipei.")
            elif team_name.strip() in data["echipe"]: st.error("Echipa există deja.")
            else:
                data["echipe"][team_name.strip()] = {"jucatori": {}, **STATS_ECHIPA}
                save_league(path, data); st.rerun()
        for name, team in data["echipe"].items():
            trophies = trofee_echipa(data, name)
            with st.expander(f"{name} · {len(team['jucatori'])} jucători" +
                             (f" · 🏆 {len(trophies)} trofee" if trophies else "")):
                st.write(f"{team['meciuri_jucate']} meciuri · {team['puncte']} puncte · "
                         f"goluri {team['goluri_marcate']}–{team['goluri_primite']}")
                with st.form(f"jucator_{name}"):
                    player_name = st.text_input("Jucător nou", key=f"pn_{name}")
                    player_position = st.selectbox("Poziție", ["Nespecificată", *POZITII_FOTBAL], key=f"pp_{name}")
                    add_player = st.form_submit_button("Adaugă în lot")
                if add_player:
                    if player_name.strip() in team["jucatori"]:
                        st.error("Jucătorul există deja în lot.")
                    elif player_name.strip():
                        team["jucatori"][player_name.strip()] = {**STATS_JUCATOR,
                            "pozitie": "" if player_position == "Nespecificată" else player_position}
                        save_league(path, data); st.rerun()
                if team["jucatori"]:
                    render_cards([{"Jucător": p, "Poziție": s.get("pozitie") or "–",
                                   **{k: v for k, v in s.items() if k not in {"pozitie", "_ajustari_statistici"}}}
                                  for p, s in team["jucatori"].items()])
                    with st.expander("Corectează statisticile unui jucător"):
                        st.caption("Corecțiile rămân salvate și după recalcularea statisticilor din istoricul meciurilor.")
                        edited_player = st.selectbox("Jucător", list(team["jucatori"]),
                            key=f"manual_stats_player_{safe_slug(name)}")
                        edited_stats = team["jucatori"][edited_player]
                        stat_fields = (("goluri", "Goluri"), ("asisturi", "Assisturi"),
                                       ("cartonase_galbene", "Cartonașe galbene"),
                                       ("cartonase_rosii", "Cartonașe roșii"))
                        stat_form_key = f"manual_stats_form_{safe_slug(name)}_{safe_slug(edited_player)}"
                        with st.form(stat_form_key):
                            corrected_values = {}
                            stat_columns = st.columns(2)
                            for index, (field, label) in enumerate(stat_fields):
                                corrected_values[field] = stat_columns[index % 2].number_input(
                                    label, min_value=0, value=int(edited_stats.get(field, 0) or 0),
                                    step=1, key=f"{stat_form_key}_{field}")
                            save_player_stats = st.form_submit_button("Salvează statisticile", type="primary")
                        if save_player_stats:
                            adjustments = edited_stats.setdefault("_ajustari_statistici", {})
                            for field, _ in stat_fields:
                                current_adjustment = int(adjustments.get(field, 0) or 0)
                                derived_value = int(edited_stats.get(field, 0) or 0) - current_adjustment
                                edited_stats[field] = int(corrected_values[field])
                                adjustments[field] = int(corrected_values[field]) - derived_value
                            save_league(path, data)
                            st.success(f"Statisticile lui {edited_player} au fost actualizate.")
                            st.rerun()
                    with st.form(f"player_position_form_{safe_slug(name)}"):
                        position_player = st.selectbox("Actualizează poziția", list(team["jucatori"]),
                            key=f"position_player_{safe_slug(name)}")
                        player_positions = ["Nespecificată", *POZITII_FOTBAL]
                        previous_position = team["jucatori"][position_player].get("pozitie", "")
                        position_index = player_positions.index(previous_position) if previous_position in player_positions else 0
                        chosen_position = st.selectbox("Poziție nouă", player_positions, index=position_index,
                            key=f"chosen_position_{safe_slug(name)}")
                        save_position = st.form_submit_button("Salvează poziția")
                    if save_position:
                        team["jucatori"][position_player]["pozitie"] = "" if chosen_position == "Nespecificată" else chosen_position
                        save_league(path, data); st.success("Poziția a fost actualizată."); st.rerun()
                    for player_name, stats in team["jucatori"].items():
                        player_trophies = trofee_jucator(data, name, player_name)
                        if player_trophies:
                            st.caption(f"🏅 {player_name}: " + " · ".join(player_trophies))
                    with st.form(f"sterge_jucator_{name}"):
                        delete_player = st.selectbox("Șterge jucător", list(team["jucatori"]), key=f"dp_{name}")
                        delete_player_btn = st.form_submit_button("Șterge din lot")
                    if delete_player_btn:
                        del team["jucatori"][delete_player]; save_league(path, data); st.rerun()
                with st.form(f"rename_team_{name}"):
                    renamed = st.text_input("Redenumește echipa", value=name, key=f"rename_value_{name}")
                    rename_button = st.form_submit_button("Salvează numele")
                if rename_button:
                    try:
                        rename_team(data, name, renamed)
                        save_league(path, data); st.success("Echipa a fost redenumită."); st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))

    if page == "Meciuri și program":
        match_tabs = st.tabs(["Rezultate", "Program", "Live"])
        with match_tabs[0]:
            if data["istoric_meciuri"]:
                st.subheader("Rezultate")
                ordered_matches = ordered_by_stage(data["istoric_meciuri"])
                render_cards([{"Etapa": m.get("etapa") or "–", "Gazdă": m["e1"],
                               "Scor": f"{m['goluri_e1']} – {m['goluri_e2']}", "Oaspeți": m["e2"],
                               "Schimbări": match_substitution_summary(m),
                               "Masa verde": "Da" if m.get("masa_verde") else ""}
                              for m in ordered_matches])
                st.markdown("#### Istoric meci și vot pentru omul meciului")
                selected_history_match = st.selectbox(
                    "Alege un meci",
                    ordered_matches,
                    format_func=lambda m: f"Etapa {m.get('etapa') or '—'} · {m.get('e1')} {m.get('goluri_e1', 0)}–{m.get('goluri_e2', 0)} {m.get('e2')}",
                    key=f"history_match_{safe_slug(league_key(selected_entry))}")
                if selected_history_match:
                    with st.container(border=True):
                        render_match_history_details(selected_history_match)
                        st.divider()
                        st.markdown("##### ⭐ Votează omul meciului")
                        render_motm_voting(data, selected_history_match, path, username, profile,
                            widget_key=f"league-{league_key(selected_entry)}-{selected_history_match.get('id')}")
                with st.expander("Editează un rezultat"):
                    match_to_edit = st.selectbox("Meci de editat", data["istoric_meciuri"],
                        format_func=lambda m: f"{m.get('etapa') or '–'} · {m['e1']} {m['goluri_e1']}–{m['goluri_e2']} {m['e2']}",
                        key="match_to_edit")
                    teams_for_edit = list(data["echipe"])
                    original_events = match_to_edit.get("evenimente", [])
                    with st.form("edit_match_form"):
                        ec1, ec2 = st.columns(2)
                        edited_home = ec1.selectbox("Gazdă", teams_for_edit,
                            index=teams_for_edit.index(match_to_edit["e1"]) if match_to_edit["e1"] in teams_for_edit else 0)
                        edited_away = ec2.selectbox("Oaspeți", teams_for_edit,
                            index=teams_for_edit.index(match_to_edit["e2"]) if match_to_edit["e2"] in teams_for_edit else min(1, len(teams_for_edit)-1))
                        edited_round = st.number_input("Etapa", min_value=0,
                            value=int(match_to_edit.get("etapa") or 0), step=1)
                        save_edit = st.form_submit_button("Salvează modificările")
                    edited_events = render_match_event_entry(data, edited_home, edited_away,
                        f"edit_{match_to_edit['id']}", initial_events=original_events)
                    if save_edit:
                        if edited_home == edited_away:
                            st.error("Alege două echipe diferite.")
                        else:
                            new_events, invalid = [], False
                            for row in edited_events:
                                player_name = str(row.get("jucator", "")).strip()
                                if not player_name:
                                    continue
                                if row.get("echipa") not in (edited_home, edited_away):
                                    st.error("Evenimentul trebuie să aparțină uneia dintre echipe."); invalid = True; break
                                if row.get("tip") == "Schimbare":
                                    incoming_player = str(row.get("intra", "")).strip()
                                    if not incoming_player or incoming_player.casefold() == player_name.casefold():
                                        st.error("Alege doi jucători diferiți pentru schimbare."); invalid = True; break
                                    new_events.append({"echipa": row["echipa"],
                                        "minut": int(row.get("minut", 1)), "tip": "Schimbare",
                                        "jucator": player_name, "intra": incoming_player})
                                    continue
                                assist_name = row.get("asist") or None
                                if assist_name == player_name:
                                    st.error("Marcatorul nu poate să-și dea assist lui însuși."); invalid = True; break
                                new_events.append({"echipa": row["echipa"],
                                    "minut": int(row.get("minut", 1)),
                                    "tip": row.get("tip", TIPURI_EVENIMENT[0]),
                                    "jucator": player_name, "asist": assist_name})
                            if not invalid:
                                old_index = data["istoric_meciuri"].index(match_to_edit)
                                old_id = match_to_edit["id"]
                                data["istoric_meciuri"].pop(old_index)
                                rebuild_stats(data)
                                corrected = build_match(edited_home, edited_away, new_events,
                                    int(edited_round) or None, walkover=match_to_edit.get("masa_verde"),
                                    reason=match_to_edit.get("motiv_mv", ""))
                                corrected["id"] = old_id
                                if "voturi_motm" in match_to_edit:
                                    corrected["voturi_motm"] = match_to_edit["voturi_motm"]
                                apply_match(data, corrected)
                                data["istoric_meciuri"].insert(old_index, data["istoric_meciuri"].pop())
                                for fixture in data["program"]:
                                    if fixture.get("meci_id") == old_id:
                                        fixture["e1"], fixture["e2"] = corrected["e1"], corrected["e2"]
                                        fixture["etapa"] = corrected.get("etapa")
                                save_league(path, data); st.success("Rezultatul a fost corectat."); st.rerun()
                with st.expander("Anulează un rezultat"):
                    selected = st.selectbox("Meci", data["istoric_meciuri"],
                        format_func=lambda m: f"{m.get('etapa') or '–'} · {m['e1']} {m['goluri_e1']}–{m['goluri_e2']} {m['e2']}")
                    if st.button("Anulează meciul selectat", type="secondary"):
                        data["istoric_meciuri"].remove(selected)
                        for fixture in data["program"]:
                            if fixture.get("meci_id") == selected.get("id"):
                                fixture["meci_id"] = None
                        rebuild_stats(data)
                        save_league(path, data); st.rerun()
        with match_tabs[1]:
            st.subheader("Înregistrează un meci")
            teams = list(data["echipe"])
            if len(teams) < 2:
                st.info("Adaugă cel puțin două echipe.")
            else:
                playable = [fixture for fixture in pending_fixtures(data)
                    if fixture.get("arbitraj_live", {}).get("faza", "programat") == "programat"]
                scheduled = st.selectbox("Meci programat (opțional)", [None, *playable],
                    format_func=lambda f: "Alege manual" if f is None else
                        f"Etapa {f.get('etapa') or '–'} · {f.get('e1')} – {f.get('e2')}" + (f" · {f.get('data')}" if f.get("data") else ""),
                    key="scheduled_fixture")
                fixture_identity = scheduled.get("id") if scheduled else "manual"
                draft_id = hashlib.sha1(str(f"{selected_entry.get('id')}:{fixture_identity}").encode()).hexdigest()[:12]
                home_default = teams.index(scheduled["e1"]) if scheduled and scheduled.get("e1") in teams else 0
                away_default = teams.index(scheduled["e2"]) if scheduled and scheduled.get("e2") in teams else min(1, len(teams)-1)
                left, right = st.columns(2)
                home = left.selectbox("Gazdă", teams, index=home_default, key=f"match_home_{draft_id}")
                away = right.selectbox("Oaspeți", teams, index=away_default, key=f"match_away_{draft_id}")
                round_no = st.number_input("Etapa (lasă 0 dacă nu se aplică)", min_value=0,
                    value=int(scheduled.get("etapa") or 0) if scheduled else 0, step=1,
                    key=f"match_round_{draft_id}")
                entry_mode = st.radio("Cum se încheie meciul?", ["Introduc evenimentele", "Victorie la masa verde (3–0)"],
                                      horizontal=True, key=f"match_mode_{draft_id}")
                walkover = entry_mode.startswith("Victorie")
                winner = reason = None
                if walkover:
                    winner = st.selectbox("Câștigătoare", [home, away], key=f"match_winner_{draft_id}")
                    reason = st.text_input("Motivul (opțional)", key=f"match_reason_{draft_id}")
                    st.info(f"Rezultatul va fi {winner} 3–0.")
                    events = []
                elif home != away:
                    events = render_match_event_entry(data, home, away, draft_id)
                else:
                    events = []
                    st.warning("Alege două echipe diferite pentru a introduce evenimentele.")
                save_match = st.button("Salvează meciul", type="primary", key=f"save_match_{draft_id}")
                if save_match:
                    if home == away:
                        st.error("Gazda și oaspeții trebuie să fie echipe diferite.")
                    else:
                        match = build_match(home, away, events, int(round_no) or None,
                                            winner if walkover else None, reason or "")
                        apply_match(data, match)
                        if scheduled:
                            scheduled["e1"], scheduled["e2"] = home, away
                            scheduled["etapa"], scheduled["meci_id"] = match.get("etapa"), match["id"]
                            scheduled["arbitraj_live"] = {"faza": "final", "half_minutes": 45, "secunde": 0,
                                "minute_extra": 0, "minute_extra_total": 0, "pornit_la": None,
                                "evenimente": copy.deepcopy(match.get("evenimente", []))}
                        st.session_state.pop(f"match_draft_{draft_id}", None)
                        save_league(path, data); st.success("Meci salvat."); st.rerun()
            st.subheader("Program")
            if len(data["echipe"]) < 2:
                st.info("Adaugă cel puțin două echipe pentru a genera programul.")
            else:
                with st.form("gen_program"):
                    twice = st.checkbox("Tur și retur")
                    make_schedule = st.form_submit_button("Generează programul")
                if make_schedule:
                    data["program"] = generate_rounds(list(data["echipe"]), twice)
                    save_league(path, data); st.rerun()
                with st.expander("Adaugă manual un meci în program"):
                    with st.form("fixture_manual"):
                        fc1, fc2, fc3, fc4 = st.columns([1, 2, 2, 2])
                        stage = fc1.number_input("Etapa", min_value=1, step=1, key="manual_stage")
                        fixture_home = fc2.selectbox("Gazdă", list(data["echipe"]), key="manual_home")
                        fixture_away = fc3.selectbox("Oaspeți", list(data["echipe"]), index=1, key="manual_away")
                        fixture_date = fc4.text_input("Data", placeholder="ZZ.LL.AAAA")
                        add_fixture = st.form_submit_button("Adaugă în program")
                    if add_fixture:
                        if fixture_home == fixture_away:
                            st.error("Alege două echipe diferite.")
                        else:
                            data["program"].append({"id": uuid.uuid4().hex[:8], "etapa": int(stage),
                                "e1": fixture_home, "e2": fixture_away, "data": fixture_date.strip(), "meci_id": None,
                                "arbitraj_cod": new_referee_code()})
                            save_league(path, data); st.success("Meciul a fost adăugat în program."); st.rerun()
            fixtures = pending_fixtures(data)
            if fixtures:
                render_cards([{"Etapa": f.get("etapa"), "Gazdă": f.get("e1"),
                               "Oaspeți": f.get("e2"), "Data": f.get("data", ""),
                               "Status": "Programat"}
                              for f in fixtures])
                if st.button("Șterge programul"):
                    data["program"] = []; save_league(path, data); st.rerun()
            elif data["program"]:
                st.success("Toate meciurile din program au fost jucate.")
        with match_tabs[2]:
            st.subheader("Meciuri live")
            render_live_matches_overview(path)

    if page == "Cupa":
        st.subheader("Cupa")
        st.caption("Alege o cupă, urmărește rundele și înregistrează fiecare tur sau retur separat.")
        teams = list(data["echipe"])
        cups = [c for c in data.get("cupe", []) if not c.get("super")]
        with st.expander("➕ Creează o cupă nouă", expanded=not cups):
            if len(teams) < 2:
                st.info("Ai nevoie de cel puțin două echipe în ligă.")
            else:
                with st.form("creare_cupa"):
                    cup_name = st.text_input("Numele cupei", f"Cupa {data['nume_liga']}")
                    participants = st.multiselect("Echipe participante", teams, default=teams)
                    st.caption("Tragerea la sorți se face automat. Dacă numărul echipelor nu se potrivește tabloului, unele primesc tur liber.")
                    create_cup = st.form_submit_button("Creează cupa", type="primary")
                if create_cup:
                    if len(participants) < 2:
                        st.error("Alege cel puțin două echipe.")
                    elif any(str(c.get("nume") or "").strip().casefold() ==
                             (cup_name.strip() or "Cupa").casefold() for c in cups):
                        st.error("Există deja o cupă cu acest nume. Alege-o din lista cupelor, nu o crea din nou.")
                    else:
                        use_home_away = data.get("setari_liga", {}).get("cup_leg_format") == "home_away"
                        new_cup = make_cup(participants, cup_name.strip() or "Cupa", use_home_away)
                        data.setdefault("cupe", []).append(new_cup)
                        st.session_state["cup_select_after_create"] = new_cup["id"]
                        save_league(path, data); st.rerun()

        cups = [c for c in data.get("cupe", []) if not c.get("super")]
        if not cups:
            st.info("Creează o cupă ca să vezi tabloul și să introduci rezultatele.")
        else:
            cups_by_id = {item["id"]: item for item in cups}
            cup_ids = list(cups_by_id)
            cup_numbers = {cup_id: index + 1 for index, cup_id in enumerate(cup_ids)}
            cup_picker_key = "active_regular_cup_" + hashlib.sha1(
                "|".join(cup_ids).encode("utf-8")).hexdigest()[:10]
            select_after_create = st.session_state.pop("cup_select_after_create", None)
            if select_after_create in cups_by_id:
                st.session_state[cup_picker_key] = select_after_create
            selected_cup_id = st.selectbox("Alege cupa de administrat", cup_ids,
                format_func=lambda cup_id: f"Cupa {cup_numbers[cup_id]} · {cups_by_id[cup_id]['nume']} · {cups_by_id[cup_id].get('status', 'în desfășurare')}",
                key=cup_picker_key)
            cup = cups_by_id[selected_cup_id]
            rounds = cup.get("runde", [])
            home_away_cup = bool(cup.get("tur_retur", False))
            pending = []
            for ri, round_data in enumerate(rounds):
                for mi, slot in enumerate(round_data.get("meciuri", [])):
                    if not slot.get("e1") or not slot.get("e2") or slot.get("castigator"):
                        continue
                    if not slot.get("meci"):
                        pending.append((ri, mi, slot, 1))
                    elif home_away_cup and not slot.get("meci_retur"):
                        pending.append((ri, mi, slot, 2))
            played_count = sum((1 if slot.get("meci") else 0) +
                               (1 if slot.get("meci_retur") else 0)
                               for round_data in rounds for slot in round_data.get("meciuri", []))
            total_games = max(1, (len(cup.get("echipe", [])) - 1) * (2 if home_away_cup else 1))
            info_cols = st.columns(3)
            info_cols[0].metric("Echipe", len(cup.get("echipe", [])))
            info_cols[1].metric("Meciuri jucate", f"{played_count} / {total_games}")
            info_cols[2].metric("Runde", len(rounds))
            st.progress(min(1.0, played_count / total_games), text="Progresul cupei")
            if cup.get("castigatoare"):
                st.success(f"🏆 {cup['castigatoare']} a câștigat {cup['nume']}!")

            with st.expander("Setări cupă și ștergere"):
                cup_has_played = any(slot.get("meci") or slot.get("meci_retur")
                    for round_data in rounds for slot in round_data.get("meciuri", []))
                cup_formats = {"Un singur meci": False, "Tur și retur": True}
                current_cup_format = bool(cup.get("tur_retur", False))
                selected_cup_format_label = st.selectbox("Formatul acestei cupe", list(cup_formats),
                    index=1 if current_cup_format else 0, disabled=cup_has_played,
                    key=f"cup_format_{cup['id']}")
                if cup_has_played:
                    st.caption("Formatul nu poate fi schimbat după înregistrarea primului rezultat.")
                elif st.button("Salvează formatul cupei", key=f"save_cup_format_{cup['id']}"):
                    cup["tur_retur"] = cup_formats[selected_cup_format_label]
                    save_league(path, data)
                    st.success("Formatul cupei a fost salvat.")
                    st.rerun()
                st.caption("Regula de departajare se ia din Setări ligă și se aplică după timpul regulamentar sau după scorul agregat al returului.")
                source_supercup_exists = any(
                    item.get("super") and item.get("sursa_cupa") == cup["id"]
                    for item in data.get("cupe", []))
                st.caption("Ștergerea elimină această cupă și statisticile obținute în meciurile ei."
                           + (" Supercupa creată din ea rămâne în istoricul competițiilor." if source_supercup_exists else ""))
                if st.button("Șterge această cupă", type="secondary", key=f"start_delete_cup_{cup['id']}"):
                    st.session_state["cup_delete_pending"] = cup["id"]
                    st.rerun()
                if st.session_state.get("cup_delete_pending") == cup["id"]:
                    st.warning(f"Confirmi ștergerea cupei «{cup['nume']}»? Acțiunea nu poate fi anulată.")
                    confirm_col, cancel_col = st.columns(2)
                    if confirm_col.button("Da, șterge cupa", type="primary", key=f"confirm_delete_cup_{cup['id']}"):
                        for round_data in cup.get("runde", []):
                            for slot in round_data.get("meciuri", []):
                                for old_match in (slot.get("meci"), slot.get("meci_retur")):
                                    if old_match:
                                        apply_player_stats(data, old_match["e1"], old_match.get("mod_e1", {}), -1)
                                        apply_player_stats(data, old_match["e2"], old_match.get("mod_e2", {}), -1)
                        data["cupe"] = [item for item in data.get("cupe", []) if item.get("id") != cup["id"]]
                        data.get("premii_alese", {}).pop(f"cupa:{cup['id']}", None)
                        for state_key in list(st.session_state):
                            if state_key.startswith(f"match_draft_cup_{cup['id']}_"):
                                st.session_state.pop(state_key, None)
                        st.session_state.pop("cup_delete_pending", None)
                        save_league(path, data)
                        st.success("Cupa a fost ștearsă.")
                        st.rerun()
                    if cancel_col.button("Păstrează cupa", key=f"cancel_delete_cup_{cup['id']}"):
                        st.session_state.pop("cup_delete_pending", None)
                        st.rerun()

            next_round = pending[0][0] if pending else None
            for ri, round_data in enumerate(rounds):
                round_slots = round_data.get("meciuri", [])
                finished = sum(1 for slot in round_slots if slot.get("castigator"))
                with st.expander(f"{round_data.get('nume', f'Runda {ri + 1}')}  ·  {finished}/{len(round_slots)} decise",
                                 expanded=(ri == next_round)):
                    for mi, slot in enumerate(round_slots):
                        home_cup, away_cup = slot.get("e1"), slot.get("e2")
                        with st.container(border=True):
                            st.caption(f"Meciul {mi + 1}")
                            played = slot.get("meci")
                            if played:
                                substitutions = match_substitution_summary(played)
                                if substitutions != "–":
                                    st.caption(f"Schimbări: {substitutions}")
                                if home_away_cup:
                                    st.markdown(f"**Tur:** {played['e1']} {played['goluri_e1']} – {played['goluri_e2']} {played['e2']}")
                                    returned = slot.get("meci_retur")
                                    if returned:
                                        substitutions = match_substitution_summary(returned)
                                        if substitutions != "–":
                                            st.caption(f"Schimbări retur: {substitutions}")
                                        st.markdown(f"**Retur:** {returned['e1']} {returned['goluri_e1']} – {returned['goluri_e2']} {returned['e2']}")
                                        aggregate_home = played["goluri_e1"] + returned["goluri_e2"]
                                        aggregate_away = played["goluri_e2"] + returned["goluri_e1"]
                                        penalty_note = " · departajare la penaltyuri" if slot.get("penalti") else ""
                                        st.caption(f"Scor agregat: {slot['e1']} {aggregate_home} – {aggregate_away} {slot['e2']} · se califică {slot.get('castigator')}{penalty_note}.")
                                        render_motm_voting(data, returned, path, username, profile,
                                            widget_key=f"cup-{cup.get('id')}-{returned.get('id')}")
                                    else:
                                        st.info("Returul nu a fost jucat încă.")
                                else:
                                    penalty_note = " · decisă la penaltyuri" if slot.get("penalti") else ""
                                    st.markdown(f"**{played['e1']}  {played['goluri_e1']} – {played['goluri_e2']}  {played['e2']}**")
                                    if slot.get("castigator"):
                                        st.caption(f"Se califică {slot.get('castigator')}{penalty_note}.")
                                render_motm_voting(data, played, path, username, profile,
                                    widget_key=f"cup-{cup.get('id')}-{played.get('id')}")
                                if st.button("Anulează acest rezultat și rundele următoare",
                                    key=f"cup_undo_{cup['id']}_{ri}_{mi}"):
                                    for old_match in clear_cup_result(cup, ri, mi):
                                        apply_player_stats(data, old_match["e1"], old_match.get("mod_e1", {}), -1)
                                        apply_player_stats(data, old_match["e2"], old_match.get("mod_e2", {}), -1)
                                    save_league(path, data); st.rerun()
                            elif slot.get("castigator"):
                                st.markdown(f"**{slot['castigator']}** avansează cu tur liber.")
                            elif home_cup and away_cup:
                                st.markdown(f"**{home_cup} — {away_cup}**")
                                st.caption("Meci de jucat")
                            else:
                                st.markdown(f"**{home_cup or 'Echipa 1'} — {away_cup or 'Echipa 2'}**")
                                st.caption("Echipele se stabilesc după runda anterioară.")

            st.markdown("### Înregistrează un rezultat")
            if pending:
                pending_ids = "_".join(f"{slot.get('id', f'{ri}-{mi}')}-{leg}"
                                        for ri, mi, slot, leg in pending)
                selected_match = st.selectbox("Alege meciul", pending,
                    format_func=lambda item: f"{rounds[item[0]].get('nume', 'Runda')} · "
                        f"{'Retur' if item[3] == 2 else ('Tur' if home_away_cup else 'Meci')} · "
                        f"{item[2]['e2'] if item[3] == 2 else item[2]['e1']} — "
                        f"{item[2]['e1'] if item[3] == 2 else item[2]['e2']}",
                    key=f"cup_pending_{cup['id']}_{pending_ids}")
                ri, mi, slot, leg = selected_match
                if leg == 2:
                    home_cup, away_cup = slot["e2"], slot["e1"]
                    first_leg = slot["meci"]
                    aggregate_before = (first_leg["goluri_e2"], first_leg["goluri_e1"])
                    leg_caption = "Returul se joacă pe terenul echipei care a fost oaspete în tur."
                else:
                    home_cup, away_cup = slot["e1"], slot["e2"]
                    aggregate_before = (0, 0)
                    leg_caption = ""
                if leg_caption:
                    st.info(leg_caption)
                cup_tie_rule = data.get("setari_liga", {}).get("cup_tie_resolution", "penalties")
                decide_tie = not (home_away_cup and leg == 1)
                cup_match, winner_name, decided_by_penalties, saved = render_knockout_result_entry(
                    data, home_cup, away_cup, f"cup_{cup['id']}_{ri}_{mi}_leg{leg}",
                    cup_tie_rule, aggregate_before, decide_tie,
                    "Salvează turul" if home_away_cup and leg == 1 else
                    ("Salvează returul și califică echipa" if leg == 2 else "Salvează rezultatul și califică echipa"),
                    f"save_cup_match_{cup['id']}_{ri}_{mi}_leg{leg}")
                if saved:
                    if leg == 1:
                        slot["meci"] = cup_match
                        if not home_away_cup:
                            slot["castigator"], slot["penalti"] = winner_name, decided_by_penalties
                            advance_cup_winner(cup, ri, mi)
                    else:
                        slot["meci_retur"] = cup_match
                        slot["castigator"], slot["penalti"] = winner_name, decided_by_penalties
                        advance_cup_winner(cup, ri, mi)
                    apply_player_stats(data, home_cup, cup_match.get("mod_e1", {}))
                    apply_player_stats(data, away_cup, cup_match.get("mod_e2", {}))
                    for suffix in ("", "_extra"):
                        st.session_state.pop(f"match_draft_cup_{cup['id']}_{ri}_{mi}_leg{leg}{suffix}", None)
                        st.session_state.pop(f"match_draft_cup_{cup['id']}_{ri}_{mi}_leg{leg}{suffix}_next", None)
                    save_league(path, data); st.rerun()
            elif cup.get("castigatoare"):
                st.success("Toate rundele s-au încheiat. Cupa are câștigătoare.")
            else:
                st.info("Nu există încă un meci disponibil. Completează meciurile rundei curente ca să se stabilească următorii adversari.")

    if page == "Supercupa":
        st.subheader("Supercupa")
        st.caption("Finala se joacă între câștigătoarea unei cupe și campioana ligii. Dacă aceeași echipă câștigă ambele trofee, adversara este echipa de pe locul 2.")
        regular_cup_winners = [c for c in data.get("cupe", [])
                               if not c.get("super") and c.get("castigatoare")]
        if len(data.get("echipe", {})) < 2:
            st.info("Adaugă cel puțin două echipe în ligă înainte să creezi Supercupa.")
        elif not regular_cup_winners:
            st.info("Termină o cupă eliminatorie. Câștigătoarea ei va juca Supercupa.")
        else:
            with st.container(border=True):
                st.markdown("#### Creează Supercupa")
                with st.form("create_supercup"):
                    source_cup = st.selectbox("Alege cupa", regular_cup_winners,
                        format_func=lambda c: f"{c.get('nume', 'Cupa')} · câștigătoare: {c['castigatoare']}")
                    preview_a, preview_b, preview_reason = participanti_supercupa(data, source_cup)
                    if preview_a:
                        st.markdown(f"**Finală propusă:** {preview_a} — {preview_b}")
                        st.caption(f"{preview_reason}. Perecherea folosește clasamentul actual al ligii.")
                    confirm_current_ranking = st.checkbox("Confirm că folosesc clasamentul actual")
                    create_supercup = st.form_submit_button("Creează finala Supercupei", type="primary")
                if create_supercup:
                    team_a, team_b, reason = participanti_supercupa(data, source_cup)
                    if not team_a:
                        st.error(reason)
                    elif not confirm_current_ranking:
                        st.warning("Confirmă folosirea clasamentului actual pentru a continua.")
                    else:
                        existing_supercups = [c for c in data.get("cupe", []) if c.get("super")]
                        super_name = "Supercupa" if not existing_supercups else f"Supercupa {len(existing_supercups) + 1}"
                        while any(c.get("nume", "").casefold() == super_name.casefold() for c in data["cupe"]):
                            super_name += " II"
                        super_home_away = data.get("setari_liga", {}).get("supercup_leg_format") == "home_away"
                        data["cupe"].append(make_supercup(super_name, team_a, team_b,
                                                          source_cup.get("id"), super_home_away))
                        save_league(path, data)
                        st.success(f"{super_name}: {team_a} — {team_b} ({reason}).")
                        st.rerun()

        supercups = [c for c in data.get("cupe", []) if c.get("super")]
        if not supercups:
            st.caption("Supercupele create vor apărea aici.")
        else:
            selected_supercup = st.selectbox("Supercupa activă", supercups,
                format_func=lambda c: f"{c.get('nume', 'Supercupa')} · {c.get('status', 'în desfășurare')}",
                key="active_supercup")
            if selected_supercup.get("castigatoare"):
                st.success(f"🏆 {selected_supercup['castigatoare']} a câștigat {selected_supercup['nume']}!")
            rounds = selected_supercup.get("runde", [])
            if not rounds or not rounds[0].get("meciuri"):
                st.info("Această Supercupă nu are încă o finală configurată.")
            else:
                final_slot = rounds[0]["meciuri"][0]
                home_super, away_super = final_slot.get("e1"), final_slot.get("e2")
                super_home_away = bool(selected_supercup.get("tur_retur", False))
                final_played = final_slot.get("meci") or final_slot.get("meci_retur")
                with st.expander("Setări Supercupă"):
                    formats = {"Un singur meci": False, "Tur și retur": True}
                    current_format_label = "Tur și retur" if super_home_away else "Un singur meci"
                    has_super_result = bool(final_slot.get("meci") or final_slot.get("meci_retur"))
                    new_format = st.selectbox("Formatul finalei", list(formats),
                        index=list(formats).index(current_format_label), disabled=has_super_result,
                        key=f"supercup_format_{selected_supercup['id']}")
                    if has_super_result:
                        st.caption("Formatul nu poate fi schimbat după înregistrarea primului rezultat.")
                    elif st.button("Salvează formatul Supercupei", key=f"save_supercup_format_{selected_supercup['id']}"):
                        selected_supercup["tur_retur"] = formats[new_format]
                        save_league(path, data); st.rerun()
                with st.container(border=True):
                    st.markdown(f"#### Finala · {home_super or '—'} — {away_super or '—'}")
                    played_super = final_slot.get("meci")
                    if played_super:
                        substitutions = match_substitution_summary(played_super)
                        if substitutions != "–":
                            st.caption(f"Schimbări: {substitutions}")
                        if super_home_away:
                            st.write(f"Tur: {played_super['e1']} {played_super['goluri_e1']} – {played_super['goluri_e2']} {played_super['e2']}")
                            returned_super = final_slot.get("meci_retur")
                            if returned_super:
                                substitutions = match_substitution_summary(returned_super)
                                if substitutions != "–":
                                    st.caption(f"Schimbări retur: {substitutions}")
                                st.write(f"Retur: {returned_super['e1']} {returned_super['goluri_e1']} – {returned_super['goluri_e2']} {returned_super['e2']}")
                                aggregate_home = played_super["goluri_e1"] + returned_super["goluri_e2"]
                                aggregate_away = played_super["goluri_e2"] + returned_super["goluri_e1"]
                                penalty_note = " · departajare la penaltyuri" if final_slot.get("penalti") else ""
                                st.caption(f"Scor agregat: {home_super} {aggregate_home} – {aggregate_away} {away_super} · câștigă {final_slot.get('castigator')}{penalty_note}.")
                                render_motm_voting(data, returned_super, path, username, profile,
                                    widget_key=f"supercup-{selected_supercup.get('id')}-{returned_super.get('id')}")
                            else:
                                st.info("Returul finalei urmează.")
                        else:
                            penalty_note = " · decisă la penaltyuri" if final_slot.get("penalti") else ""
                            if final_slot.get("castigator"):
                                st.write(f"{played_super['goluri_e1']} – {played_super['goluri_e2']} · câștigă **{final_slot.get('castigator')}**{penalty_note}")
                        render_motm_voting(data, played_super, path, username, profile,
                            widget_key=f"supercup-{selected_supercup.get('id')}-{played_super.get('id')}")
                    if final_played and st.button("Anulează rezultatul finalei", key=f"supercup_undo_{selected_supercup['id']}"):
                        for old_match in clear_cup_result(selected_supercup, 0, 0):
                            apply_player_stats(data, old_match["e1"], old_match.get("mod_e1", {}), -1)
                            apply_player_stats(data, old_match["e2"], old_match.get("mod_e2", {}), -1)
                        save_league(path, data); st.rerun()
                    if home_super and away_super and (
                            not played_super or (super_home_away and not final_slot.get("meci_retur"))):
                        leg = 2 if played_super and super_home_away else 1
                        if leg == 2:
                            match_home, match_away = away_super, home_super
                            aggregate_before = (played_super["goluri_e2"], played_super["goluri_e1"])
                            st.markdown("### Înregistrează returul")
                        else:
                            match_home, match_away = home_super, away_super
                            aggregate_before = (0, 0)
                            if super_home_away:
                                st.markdown("### Înregistrează turul")
                        super_tie_rule = data.get("setari_liga", {}).get("supercup_tie_resolution", "penalties")
                        final_match, winner, decided_by_penalties, save_final = render_knockout_result_entry(
                            data, match_home, match_away,
                            f"supercup_{selected_supercup['id']}_leg{leg}", super_tie_rule,
                            aggregate_before, decide=not (super_home_away and leg == 1),
                            button_label="Salvează turul" if super_home_away and leg == 1 else
                                ("Salvează returul și câștigătoarea" if leg == 2 else "Salvează rezultatul final"),
                            button_key=f"save_supercup_{selected_supercup['id']}_leg{leg}")
                        if save_final:
                            if leg == 1:
                                final_slot["meci"] = final_match
                                if not super_home_away:
                                    final_slot["castigator"] = winner
                                    final_slot["penalti"] = decided_by_penalties
                                    advance_cup_winner(selected_supercup, 0, 0)
                            else:
                                final_slot["meci_retur"] = final_match
                                final_slot["castigator"] = winner
                                final_slot["penalti"] = decided_by_penalties
                                advance_cup_winner(selected_supercup, 0, 0)
                            apply_player_stats(data, match_home, final_match.get("mod_e1", {}))
                            apply_player_stats(data, match_away, final_match.get("mod_e2", {}))
                            for suffix in ("", "_extra"):
                                state_prefix = f"match_draft_supercup_{selected_supercup['id']}_leg{leg}{suffix}"
                                st.session_state.pop(state_prefix, None)
                                st.session_state.pop(state_prefix + "_next", None)
                            save_league(path, data); st.rerun()

    if page == "Transferuri":
        st.subheader("Transferuri de jucători")
        team_names = list(data["echipe"])
        if len(team_names) < 2:
            st.info("Adaugă cel puțin două echipe pentru a face transferuri.")
        else:
            with st.form("transfer_jucator"):
                source = st.selectbox("Pleacă de la", team_names)
                available_players = list(data["echipe"][source]["jucatori"])
                if available_players:
                    transferred_player = st.selectbox("Jucător", available_players)
                    destination = st.selectbox("Merge la", [t for t in team_names if t != source])
                    new_player_name = st.text_input("Nume în lotul nou (opțional)")
                    make_transfer = st.form_submit_button("Transferă jucătorul")
                else:
                    transferred_player, destination, new_player_name, make_transfer = None, None, "", False
                    st.caption("Echipa aleasă nu are jucători în lot.")
            if make_transfer and transferred_player:
                try:
                    transfer_player(data, transferred_player, source, destination, new_player_name)
                    rebuild_stats(data)
                    save_league(path, data); st.success("Transferul a fost salvat."); st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        if data.get("transferuri"):
            st.markdown("#### Istoric transferuri")
            render_cards([{"Data": t.get("data", ""), "Jucător": t.get("nume_nou", t.get("jucator")),
                           "De la": t.get("de_la"), "La": t.get("la")} for t in reversed(data["transferuri"])],
                         )

    if page == "Statistici":
        st.subheader("Statistici jucători")
        st.caption("Alege un top, ca în aplicația principală. Valorile se actualizează după înregistrarea meciurilor.")
        stat_sections = (
            ("⚽ Marcatori", "goluri", "Goluri"),
            ("🎯 Asistenți", "asisturi", "Assisturi"),
            ("🟨 Galbene", "cartonase_galbene", "Galbene"),
            ("🟥 Roșii", "cartonase_rosii", "Roșii"),
        )
        stat_tabs = st.tabs([title for title, _, _ in stat_sections])
        for tab, (title, field, label) in zip(stat_tabs, stat_sections):
            with tab:
                rows = player_leaderboard(data, field, label)
                if rows:
                    render_cards(rows)
                else:
                    st.info("Încă nu există date pentru acest top.")

    if page == "Premii sezon":
        st.subheader("Premii de sezon")
        if data.get("setari_liga", {}).get("award_voting_mode", "direct") == "vote":
            st.caption("Premiile individuale care nu se acordă automat se stabilesc prin vot: fiecare votant ordonează cinci jucători, iar punctele 5–4–3–2–1 se calculează la închiderea votului.")
        else:
            st.caption("Proprietarul sau editorul alege câștigătorii direct. Clasamentul și statisticile sunt sugestii, nu acordă premii automat.")
        pending_fixture_count = len(pending_fixtures(data))
        pending_cups = sum(1 for c in data.get("cupe", []) if not c.get("castigatoare"))
        if pending_fixture_count or pending_cups:
            st.info(f"Sezonul este încă în desfășurare: {pending_fixture_count} meciuri de ligă și {pending_cups} cupe fără câștigător. Poți acorda premiile oricând.")
        teams_ranked = ranking(data)
        player_rows = [(team_name, player, stats) for team_name, team in data["echipe"].items()
                       for player, stats in team.get("jucatori", {}).items()]
        player_rows.sort(key=lambda row: (row[1].casefold(), row[0].casefold()))
        award_options = [("", "")] + [(team_name, player) for team_name, player, _ in player_rows]

        def award_label(choice):
            team_name, player = choice
            if not player:
                return "— Neacordat —"
            stats = data["echipe"].get(team_name, {}).get("jucatori", {}).get(player, {})
            position = stats.get("pozitie")
            details = f" · ⚽ {stats.get('goluri', 0)} · 🎯 {stats.get('asisturi', 0)}"
            return f"{player} · {team_name}" + (f" · {position}" if position else "") + details

        suggestions = {"campioana": (teams_ranked[0]["Echipă"] if teams_ranked else "Nicio echipă încă")}
        def event_totals(matches):
            result = {}
            for played_match in matches:
                for event in played_match.get("evenimente", []):
                    player_name = event.get("jucator")
                    if not player_name or event.get("tip") not in TIPURI_GOL:
                        continue
                    key = (event.get("echipa") or "", player_name)
                    totals = result.setdefault(key, {"goluri": 0, "asisturi": 0})
                    totals["goluri"] += 1
                    assist_name = event.get("asist")
                    if assist_name:
                        result.setdefault((key[0], assist_name), {"goluri": 0, "asisturi": 0})["asisturi"] += 1
            return result

        league_events = event_totals(data.get("istoric_meciuri", []))
        cup_matches = [match for cup_data in data.get("cupe", []) if not cup_data.get("super")
                       for round_data in cup_data.get("runde", []) for slot in round_data.get("meciuri", [])
                       for match in (slot.get("meci"), slot.get("meci_retur")) if match]
        cup_events = event_totals(cup_matches)
        combined_events = {}
        for group in (league_events, cup_events,
                      event_totals([match for cup_data in data.get("cupe", []) if cup_data.get("super")
                                    for round_data in cup_data.get("runde", []) for slot in round_data.get("meciuri", [])
                                    for match in (slot.get("meci"), slot.get("meci_retur")) if match])):
            for player_key, numbers in group.items():
                total = combined_events.setdefault(player_key, {"goluri": 0, "asisturi": 0})
                total["goluri"] += numbers["goluri"]
                total["asisturi"] += numbers["asisturi"]

        def leader_text(totals, metric, score=None):
            scores = {key: (score(value) if score else value[metric]) for key, value in totals.items()}
            best = max(scores.values(), default=0)
            if best <= 0:
                return ""
            winners = [f"{player} · {team}" for (team, player), value in scores.items() if value == best]
            return f"{' / '.join(sorted(winners))} ({best})"

        goal_hint = leader_text(league_events, "goluri")
        cup_goal_hint = leader_text(cup_events, "goluri")
        ballon_hint = leader_text(combined_events, "goluri", lambda value: value["goluri"] * 2 + value["asisturi"])
        if goal_hint:
            suggestions["gheata_liga"] = goal_hint + " goluri"
        if cup_goal_hint:
            suggestions["gheata_cupa"] = cup_goal_hint + " goluri"
        if ballon_hint:
            suggestions["balon"] = ballon_hint + " puncte · 2/gol + 1/assist"
        for cup_item in data.get("cupe", []):
            if cup_item.get("castigatoare"):
                suggestions[f"cupa:{cup_item.get('id')}"] = f"{cup_item['castigatoare']} (câștigătoare)"

        for award_index, award in enumerate(definitii_premii(data)):
            current = data.get("premii_alese", {}).get(award["cheie"], {})
            with st.container(border=True):
                st.markdown(f"#### {award['titlu']}")
                suggestion = suggestions.get(award["cheie"])
                if suggestion and not award_is_automatic(award):
                    st.caption(f"Sugestie din datele actuale: {suggestion}")
                if award_is_automatic(award):
                    winners = award_winners(data, award)
                    if winners:
                        winner_text = " / ".join(
                            team if award["tip"] == "echipa" else f"{player} · {team}"
                            for team, player in winners)
                        st.success(f"Câștigător automat: {winner_text}")
                    else:
                        st.info("Câștigătorul va apărea automat după ce există rezultate.")
                    continue
                if award["tip"] == "echipa":
                    candidates = ["— Neacordat —", *sorted(data["echipe"], key=str.casefold)]
                    existing = current.get("echipa", "")
                    default_index = candidates.index(existing) if existing in candidates else 0
                    with st.form(f"award_form_{award_index}_{safe_slug(award['cheie'])}"):
                        winner = st.selectbox("Câștigătoare", candidates, index=default_index,
                            key=f"award_team_{award_index}_{safe_slug(award['cheie'])}")
                        save_award = st.form_submit_button("Salvează alegerea", type="primary")
                    chosen_value = {"echipa": "" if winner == "— Neacordat —" else winner, "jucator": ""}
                    if save_award:
                        data.setdefault("premii_alese", {})[award["cheie"]] = {
                            **chosen_value, "modificat": int(dt.datetime.now().timestamp() * 1000)}
                        save_league(path, data)
                        st.success("Premiul a fost salvat.")
                        st.rerun()
                elif data.get("setari_liga", {}).get("award_voting_mode", "direct") == "vote":
                    st.caption("Premiile pentru echipe se aleg direct de proprietar/editor; acest premiu se decide prin vot.")
                    render_award_ballot(data, award, path, username,
                        guest_entry if guest_entry and guest_entry.get("access_method") == "legacy" else None,
                        widget_key=f"league-{league_key(selected_entry)}-{award['cheie']}")
                else:
                    ordered = list(award_options)
                    target_position = award.get("poz")
                    if target_position:
                        ordered = [ordered[0]] + sorted(ordered[1:], key=lambda choice:
                            (0 if target_position in str(data["echipe"].get(choice[0], {}).get("jucatori", {}).get(choice[1], {}).get("pozitie", "")).casefold() else 1,
                             award_label(choice).casefold()))
                    current_choice = (current.get("echipa", ""), current.get("jucator", ""))
                    default_index = ordered.index(current_choice) if current_choice in ordered else 0
                    with st.form(f"award_form_{award_index}_{safe_slug(award['cheie'])}"):
                        winner = st.selectbox("Câștigător", ordered, index=default_index,
                            format_func=award_label, key=f"award_player_{award_index}_{safe_slug(award['cheie'])}",
                            disabled=len(ordered) == 1)
                        save_award = st.form_submit_button("Salvează alegerea", type="primary", disabled=len(ordered) == 1)
                    chosen_value = {"echipa": winner[0], "jucator": winner[1]}
                    if save_award:
                        data.setdefault("premii_alese", {})[award["cheie"]] = {
                            **chosen_value, "modificat": int(dt.datetime.now().timestamp() * 1000)}
                        save_league(path, data)
                        st.success("Premiul a fost salvat.")
                        st.rerun()

    if page == "Membri":
        st.subheader("Membri și acces la ligă")
        if role != "owner":
            st.info("Doar proprietarul ligii poate administra accesul membrilor.")
            st.write(f"Proprietar: **@{owner}** · Rolul tău: **{'Editor' if role == 'editor' else 'Vizitator'}**")
        else:
            previous_codes = data.get("coduri_invitat", {})
            previous_codes = copy.deepcopy(previous_codes) if isinstance(previous_codes, dict) else {}
            codes = data["coduri_invitat"] = copy.deepcopy(previous_codes)
            if not codes.get("spectator"):
                codes["spectator"] = new_access_code()
            if not codes.get("editor"):
                codes["editor"] = new_access_code()
            if codes != previous_codes:
                save_league(path, data)
            st.markdown("#### Coduri de acces pentru această ligă")
            st.caption("Codurile sunt aceleași pentru toți invitații. Le poți copia o singură dată și le poți schimba oricând.")
            code_col1, code_col2 = st.columns(2, gap="large")
            for col, code_type, title, description in (
                    (code_col1, "spectator", "👁 Cod spectator", "Invitatul alege dacă este jucător sau doar spectator."),
                    (code_col2, "editor", "✏️ Cod editor", "Invitatul intră direct și poate modifica liga.")):
                with col:
                    with st.container(border=True):
                        st.markdown(f"### {title}")
                        st.code(codes[code_type], language=None)
                        st.caption(description)
                        if st.button("Generează cod nou", key=f"rotate_{code_type}"):
                            data["coduri_invitat"][code_type] = new_access_code()
                            save_league(path, data)
                            st.rerun()
            st.info("Invitații introduc codul pe ecranul de autentificare. Schimbarea unui cod dezactivează imediat codul vechi.")

            st.divider()
            data.setdefault("membri", [])
            if data["membri"]:
                st.markdown("#### Acces acordat")
                for index, member in enumerate(list(data["membri"])):
                    member_name = member.get("username", "?")
                    with st.container(border=True):
                        m1, m2, m3 = st.columns([2, 2, 1])
                        m1.markdown(f"**@{member_name}** · {'Jucător' if member.get('tip') == 'jucator' else 'Spectator'}")
                        new_role = m2.selectbox("Rol", ["editor", "vizitator"],
                            index=0 if member.get("rol") == "editor" else 1,
                            format_func=lambda r: "Editor" if r == "editor" else "Vizitator",
                            key=f"member_role_{index}_{member_name}")
                        if m2.button("Salvează rolul", key=f"save_role_{index}_{member_name}"):
                            next(m for m in data["membri"] if m.get("username") == member_name)["rol"] = new_role
                            save_league(path, data); st.success("Rol actualizat."); st.rerun()
                        if m3.button("Revocă", key=f"revoke_{index}_{member_name}"):
                            data["membri"] = [m for m in data["membri"] if m.get("username") != member_name]
                            save_league(path, data); st.success("Acces revocat."); st.rerun()
                        linked = load_users().get(member_name, {}).get("selectii_ligi", {}).get(league_key(selected_entry))
                        if linked:
                            st.caption(f"Alegerea profilului: {linked.get('echipa')} · {linked.get('jucator')} ({linked.get('pozitie') or 'poziție nespecificată'})")
            else:
                st.info("Nu ai partajat această ligă cu niciun cont încă.")

    if page == "Profil":
        st.subheader("Profil personal")
        today = dt.date.today()
        birthday_value = today.replace(year=today.year - 12)
        try:
            birthday_value = dt.datetime.strptime(profile.get("data_nasterii", ""), "%d.%m.%Y").date()
        except (ValueError, TypeError):
            pass
        with st.form("profile_details"):
            display_name = st.text_input("Nume și prenume", value=profile.get("nume", username))
            account_email = st.text_input("Adresă de e-mail", value=profile.get("email", ""),
                                          help="După salvare, te vei putea conecta și cu această adresă.")
            birthday = st.date_input("Data nașterii", value=min(birthday_value, today),
                                     min_value=dt.date(1900, 1, 1), max_value=today)
            professional = st.selectbox("Joci la un club profesionist?", ["Da", "Nu"],
                index=0 if profile.get("joaca_fotbal") == "Da" else 1)
            positions = list(POZITII_FOTBAL)
            position = st.selectbox("Poziția ta", positions,
                index=positions.index(profile["pozitie"]) if profile.get("pozitie") in positions else 0)
            save_profile = st.form_submit_button("Salvează profilul")
        if save_profile:
            users = load_users()
            normalized_email = account_email.strip().casefold()
            email_in_use = any(user_key != username and
                str(user_record.get("email", "")).strip().casefold() == normalized_email
                for user_key, user_record in users.items()) if normalized_email else False
            if normalized_email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized_email):
                st.error("Introdu o adresă de e-mail validă.")
            elif email_in_use:
                st.error("Adresa aceasta este deja folosită de alt cont.")
            else:
                users[username].update({"nume": display_name.strip() or username,
                    "email": normalized_email,
                    "data_nasterii": birthday.strftime("%d.%m.%Y"),
                    "joaca_fotbal": professional, "pozitie": position})
                save_users(users); st.success("Profilul a fost salvat. Te poți conecta și cu e-mailul."); st.rerun()

        st.markdown("#### Parolă")
        with st.form("change_account_password"):
            old_password = st.text_input("Parola curentă", type="password")
            new_password = st.text_input("Parola nouă", type="password")
            new_password_confirm = st.text_input("Confirmă parola nouă", type="password")
            change_password = st.form_submit_button("Schimbă parola")
        if change_password:
            if not verify_password(profile, old_password):
                st.error("Parola curentă este greșită.")
            elif len(new_password) < 6:
                st.error("Parola nouă trebuie să aibă cel puțin 6 caractere.")
            elif new_password != new_password_confirm:
                st.error("Parolele noi nu coincid.")
            else:
                users = load_users()
                salt, digest = password_hash(new_password)
                users[username].update({"sare": salt, "hash": digest,
                    "iteratii": PASSWORD_ITERATIONS, "dispozitive": []})
                save_users(users); st.success("Parola a fost schimbată."); st.rerun()

        st.markdown("#### Alege-ți echipa și jucătorul")
        if paths:
            personal_league = st.selectbox("Liga", paths,
                format_func=lambda item: f"{load_league(item['path']).get('nume_liga', item['path'].stem)} · @{item['owner']}",
                key="profile_league")
            personal_data = load_league(personal_league["path"])
            personal_teams = list(personal_data["echipe"])
            if personal_teams:
                selected_key = league_key(personal_league)
                prior = profile.setdefault("selectii_ligi", {}).get(selected_key, {})
                with st.form("profile_team_link"):
                    selected_team = st.selectbox("Echipa", personal_teams,
                        index=personal_teams.index(prior["echipa"]) if prior.get("echipa") in personal_teams else 0)
                    player_options = list(personal_data["echipe"][selected_team].get("jucatori", {}))
                    if player_options:
                        selected_player = st.selectbox("Jucător din lot", player_options,
                            index=player_options.index(prior["jucator"]) if prior.get("jucator") in player_options else 0)
                    else:
                        selected_player = None
                        st.caption("Echipa nu are încă jucători în lot.")
                    save_link = st.form_submit_button("Salvează asocierea", disabled=not bool(player_options))
                if save_link and selected_player:
                    users = load_users()
                    users[username].setdefault("selectii_ligi", {})[selected_key] = {
                        "echipa": selected_team, "jucator": selected_player,
                        "pozitie": profile.get("pozitie", ""), "actualizat": dt.datetime.now().timestamp()}
                    save_users(users); st.success("Profilul a fost asociat jucătorului."); st.rerun()
            else:
                st.info("Adaugă echipe în ligă pentru a-ți asocia un jucător.")
        totals = dict(STATS_JUCATOR)
        totals["omul_meciului"] = 0
        associations = []
        for league_entry in paths:
            league_data = load_league(league_entry["path"])
            selection = (profile.get("selectii_ligi", {}).get(league_key(league_entry)) or
                         league_data.get("selectii_membri", {}).get(username))
            if not selection:
                continue
            team_name, player_name = selection.get("echipa"), selection.get("jucator")
            stats = league_data.get("echipe", {}).get(team_name, {}).get("jucatori", {}).get(player_name)
            if not stats:
                continue
            for stat in totals:
                if stat != "omul_meciului":
                    totals[stat] += int(stats.get(stat, 0) or 0)
            motm_count = motm_wins_for_player(league_data, team_name, player_name)
            totals["omul_meciului"] += motm_count
            associations.append((league_data.get("nume_liga", league_entry["path"].stem), team_name,
                                 player_name, stats, trofee_jucator(league_data, team_name, player_name), motm_count))
        st.markdown("#### Statisticile mele")
        mcols = st.columns(5)
        for col, title, field in zip(mcols, ("Goluri", "Assisturi", "Galbene", "Roșii", "Omul meciului"),
                                     ("goluri", "asisturi", "cartonase_galbene", "cartonase_rosii", "omul_meciului")):
            col.metric(title, totals[field])
        if associations:
            render_cards([{"Ligă": league, "Echipă": team, "Jucător": player,
                "Goluri": stats.get("goluri", 0), "Assisturi": stats.get("asisturi", 0),
                "Galbene": stats.get("cartonase_galbene", 0), "Roșii": stats.get("cartonase_rosii", 0),
                "Omul meciului": motm_count,
                "Trofee": " · ".join(trophies) if trophies else "–"}
                for league, team, player, stats, trophies, motm_count in associations])
        else:
            st.caption("Asociază un jucător cu profilul tău pentru a vedea statisticile personale.")

    if page == "Import / export":
        st.subheader("Import / export JSON")
        upload = st.file_uploader("Importă un fișier JSON de ligă", type=["json"], key="import_json")
        if upload and st.button("Importă peste liga activă"):
            try:
                imported = normalizeaza_date(json.loads(upload.getvalue().decode("utf-8")))
                save_league(path, imported); st.success("Liga a fost importată."); st.rerun()
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                st.error(f"Fișierul nu este un JSON de ligă valid: {exc}")
        st.download_button("Descarcă liga activă", json.dumps(data, ensure_ascii=False, indent=2),
                           file_name=f"{safe_slug(data['nume_liga'])}.json", mime="application/json")
        st.caption("Datele sunt stocate în Supabase." if SUPABASE_ENABLED else
                   f"Mod local · date ligi: `{BASE_DIR}` · conturi: `{USERS_FILE}`. Pentru Streamlit Cloud configurează SUPABASE_URL și SUPABASE_SERVICE_ROLE_KEY.")


if __name__ == "__main__":
    main()
