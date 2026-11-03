# Nginx Reverse Proxy Sozlamalari

Ushbu yo'riqnoma serverda (Ubuntu/Debian) Nginx orqali PhishGuard Admin paneli va API ni standart 80 (yoki 443 HTTPS) portda ishga tushirish uchun mo'ljallangan.

---

## 1. Nginx o'rnatish (agar o'rnatilmagan bo'lsa)
```bash
sudo apt update
sudo apt install nginx -y
```

---

## 2. Konfiguratsiyani o'rnatish
```bash
# Konfiguratsiya faylini Nginx katalogiga nusxalash
sudo cp nginx/nginx.conf /etc/nginx/sites-available/phishguard

# Saytni faollashtirish
sudo ln -s /etc/nginx/sites-available/phishguard /etc/nginx/sites-enabled/

# Standart default saytni o'chirish (ixtiyoriy)
sudo rm -f /etc/nginx/sites-enabled/default

# Konfiguratsiyani tekshirish
sudo nginx -t

# Nginx ni qayta ishga tushirish
sudo systemctl reload nginx
```

---

## 3. Firewall (UFW) sozlamalari
Serveringizda 80 va 443 portlar ochiqligiga ishonch hosil qiling:
```bash
sudo ufw allow 'Nginx Full'
# yoki
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
```

---

## 4. Foydalanish
Endi brauzerda to'g'ridan-to'g'ri serveringiz IP manzilini oching:
`http://<SERVER_IP>/`

Siz darhol **PhishGuard Kiberxavfsizlik Login Sahifasi**ga yo'naltirilasiz:
- **Email:** `admin@phishguard.uz`
- **Parol:** `AdminPhishGuard2025!`

