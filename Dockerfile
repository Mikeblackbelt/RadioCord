FROM python:3.11-slim

# Install ffmpeg
RUN apt update && apt install -y ffmpeg && apt clean

# Set working directory
WORKDIR /app

# Copy your bot code into the container
COPY . .

# Install dependencies
RUN pip install -r requirements.txt

# Run the bot
CMD ["python", "main.py"]
