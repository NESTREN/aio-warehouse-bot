# 🏬 Складской Telegram‑бот на aiogram

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![aiogram](https://img.shields.io/badge/aiogram-v3-success)
![DB](https://img.shields.io/badge/DB-SQLite-lightgrey)
![License](https://img.shields.io/badge/License-MIT-black)

**Современный склад‑бот для бизнеса**: удобные кнопки, учет остатков, склады, отчеты и массовая загрузка — все прямо в Telegram.

---

## 🎬 Демо (GIF)

> Вставьте сюда ваш GIF с демонстрацией работы бота и меню:

```
![Демо работы бота](docs/demo.gif)
```

---

## ✅ Главные преимущества

| Преимущество | Что дает |
|---|---|
| 🔒 Админ‑доступ | Бот доступен только разрешенным пользователям |
| ⚡ Быстрый ввод | Кнопки, подсказки, автозаполнение похожих товаров |
| 🧠 Умный поиск | Поиск по товарам и фильтрация по складам |
| 📦 Склады | Привязка товара к складу + сортировка |
| 📊 Отчеты | CSV‑экспорт и история движений |
| 🚀 Быстрый старт | Установка и запуск за считанные минуты |

---

## 🧩 Возможности

- ➕ Добавление товаров
- ➖ Изменение остатка (+/−)
- ✅ Установка остатка
- 🔍 Поиск по товарам
- 🏢 Фильтр товаров по складу + сортировка
- ⚠️ Низкие остатки
- 📤 Экспорт CSV
- 🧾 История движений
- 🛠️ Админ‑панель
- 🏬 Управление складами
- 📥 Массовая загрузка

---

## 🖼️ Скриншоты

Добавьте сюда изображения интерфейса:

```
![Меню](docs/menu.png)
![Склад](docs/warehouse.png)
```

---

## 🚀 Быстрый старт (3 шага)

1. Установить зависимости:
   ```bash
   pip install -r requirements.txt
   ```
2. Создать `.env` в корне проекта:
   ```
   BOT_TOKEN=ВАШ_ТОКЕН_БОТА
   SUPERADMINS=123456789
   DB_PATH=data.db
   ```
3. Запустить:
   ```bash
   python main.py
   ```

---

## 🪟 Запуск на Windows

1. Установите Python 3.10+
2. Откройте PowerShell в папке проекта
3. Выполните:

```powershell
pip install -r requirements.txt
python main.py
```

Чтобы бот работал постоянно — используйте отдельную консоль или **Планировщик задач Windows**.

---

## 🐧 Запуск на Linux / VPS (systemd)

### 1) Подготовка

```bash
sudo apt update
sudo apt install -y python3 python3-pip
```

### 2) Установка зависимостей

```bash
pip3 install -r requirements.txt
```

### 3) Сервис systemd

Создайте файл `/etc/systemd/system/warehouse-bot.service`:

```ini
[Unit]
Description=Warehouse Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/warehouse-bot
ExecStart=/usr/bin/python3 /home/ubuntu/warehouse-bot/main.py
Restart=always
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

### 4) Запуск сервиса

```bash
sudo systemctl daemon-reload
sudo systemctl enable warehouse-bot
sudo systemctl start warehouse-bot
sudo systemctl status warehouse-bot
```

---

## 📥 Массовая загрузка товаров

Формат CSV через запятую (по одной строке):

```
sku,name,qty,unit,location,warehouse,min_qty
```

Пример:

```
A-001,Кабель USB,10,шт,Стеллаж 1,Склад А,2
A-002,Адаптер,5,шт,,Склад А,0
A-003,Клавиатура,7
```

---

## ❓ FAQ

**Почему бот не отвечает?**
- Проверьте, что вы админ (`SUPERADMINS` содержит ваш Telegram ID).
- Убедитесь, что запущена только одна копия бота.

**Где база данных?**
- По умолчанию `data.db` в корне проекта.

---

## 🧱 Стек

- Python 3.10+
- aiogram v3
- SQLite + aiosqlite

---

## 👨‍💻 Разработчик

**Юрий**

---

## 📌 Roadmap (идеи на развитие)

- 📦 Остатки по нескольким складам для одного товара
- 📈 Расширенная аналитика и графики
- 🔔 Уведомления о критических остатках
- 🧾 Экспорт в Excel и Google Sheets
- 🤝 Роли админов (склад / менеджер / руководитель)

---

## 📄 Лицензия

MIT (можно поменять на нужную)
