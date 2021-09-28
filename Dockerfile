FROM alpine:latest

RUN apk --no-cache add python3 py3-pip \
    && pip install requests 

ADD tagger.py /home/tagger.py
