# Smartslide

This is a web application which will be a tremendous help to people taking online classes.

The user will upload a video of the class and the slides concerned and we return them the slides with separate subtitiles and audio files for each slide.

People who have doubts in just specific slides can use this web application to ease their learning instead of scrougning the video for some info. Similarly since we generate subtitiles for each slide, it is even more easier for people to revise all the content.

## Instructions to run

Create a conda environment with necessary packages
```
conda create --name flask python=3.8
conda activate flask
conda install flask flask-sqlalchemy flask-login
```

Inside the project directory, do:
```
export FLASK_APP=project
flask run
```
to get the server up and running on localhost:5000
