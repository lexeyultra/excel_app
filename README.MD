Docker (Для продвинутых / сервера)
Если вам нужно запустить это как сервер в интернете или внутри компании:

Создайте файл Dockerfile в той же папке:
dockerfile

FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py"]

Соберите образ: docker build -t my-excel-app .
Запустите: docker run -p 8501:8501 my-excel-app
