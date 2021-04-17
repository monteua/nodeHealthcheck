FROM python:3.8
COPY . /node
WORKDIR /node
RUN pip install -r requirements.txt
CMD python ./bot.py