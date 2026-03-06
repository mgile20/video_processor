# Use an official Python base image
FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y ffmpeg exiftool && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /code

# Copy the requirements file first (better for caching layers)
COPY ./requirements.txt /code/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the rest of the application code
COPY ./app /code/app
COPY run.py /code/run.py

CMD ["python", "run.py"]