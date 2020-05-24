# Pull base image
FROM python:3.8-slim-buster

RUN apt-get update
RUN apt-get install build-essential libffi-dev -y

# Set environment varibles
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /

# Install dependencies
RUN pip install --upgrade pip
RUN pip install pipenv
COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
