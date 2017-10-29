FROM python:3

ADD app.py /
ADD requirements.txt /
COPY static /static
COPY templates /templates

RUN pip install -r requirements.txt

EXPOSE 5000

ENV FLASK_APP app.py

ENTRYPOINT ["flask"]
CMD ["run", "--host", "0.0.0.0"]
