# export_kml

Простое Flask-приложение для экспорта геозон в KML через веб-форму.

## Установка

```bash
# 1. Клонировать репозиторий
git clone https://github.com/your_user/export_kml.git
cd export_kml

# 2. Создать виртуальное окружение и установить зависимости
python3.10 -m venv venv
source venv/bin/activate
pip install --no-cache-dir -r requirements.txt
```

## Запуск (Gunicorn + systemd)

1. Создать сервис-файл `/etc/systemd/system/export_kml.service`:
   ```ini
   [Unit]
   Description=Flask export_kml
   After=network.target

   [Service]
   User=appuser
   WorkingDirectory=/opt/export_kml
   ExecStart=/opt/export_kml/venv/bin/gunicorn -w 4 export_kml:app --bind 127.0.0.1:8000
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
2. Активировать и запустить сервис:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable export_kml
   sudo systemctl start export_kml
   ```

## Nginx

В существующем блоке `server` добавить:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

Перезагрузить Nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Доступ

Открыть в браузере:
```
http://your.domain/
```

