FROM python:3.11.0a1-alpine3.14

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

EXPOSE 5000

ENV envfile .env

RUN python -m spacy download en_core_web_sm

CMD [ "aiofauna", "run", "--port", "5000" ]