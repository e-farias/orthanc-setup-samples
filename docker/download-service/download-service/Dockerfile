FROM python:3.8

RUN pip install requests
RUN pip install flask

RUN mkdir /app

ADD . /

CMD [ "python", "-u", "/download-service.py" ]