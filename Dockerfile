FROM python:3.12-slim
WORKDIR /app
COPY NovelChapterCheck.py requirements.txt novel_links.txt results.json .env ./
RUN pip install -r requirements.txt
EXPOSE 8080
CMD ["python", "NovelChapterCheck.py"]