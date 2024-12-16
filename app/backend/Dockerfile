FROM python:3.11-bullseye

WORKDIR /backend

COPY ./requirements.txt /backend/requirements.txt

RUN python -m pip install --no-cache-dir --upgrade -r requirements.txt

COPY ./chat.py /backend/ 
COPY ./config.py /backend/

CMD ["fastapi", "run", "chat.py", "--port", "80"]
