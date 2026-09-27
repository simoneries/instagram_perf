from instagrapi import Client
import pandas as pd
import numpy as np
import json
import os
from dotenv import load_dotenv, dotenv_values 
import requests
import time

#Authentification 

#Get .env variables
load_dotenv()
ENV_PROXY_ADRESS = os.getenv("PROXY_ADRESS")
ENV_PROXY_PORT = os.getenv("PROXY_PORT")
ENV_PROXY_USERNAME = os.getenv("PROXY_USERNAME")
ENV_PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")

ENV_IG_USERNAME = os.getenv("IG_USERNAME")
ENV_IG_PASSWORD = os.getenv("IG_PASSWORD")


#Define the proxy adress
proxy = f'http://{ENV_PROXY_USERNAME}:{ENV_PROXY_PASSWORD}@{ENV_PROXY_ADRESS}:{ENV_PROXY_PORT}'


cl = Client()

try:
    cl.load_settings("session.json")
    cl.login(ENV_IG_USERNAME,ENV_IG_PASSWORD)

except FileNotFoundError:
    cl.set_proxy(proxy)
    cl.login(ENV_IG_USERNAME,ENV_IG_PASSWORD)
    settings = cl.get_settings()
    settings["proxy"] = proxy

    with open("session.json","w") as f:
        json.dump(settings,f)


def get_medias(user):
    #Get user 
    user = cl.user_info_by_username(user)

    #Get medias from user and stores it into a dataFrame
    time.sleep(2)
    medias = cl.user_medias(user.pk,amount=3)
    rows = [media.model_dump(mode = "json") for media in medias]
    df = pd.DataFrame(rows)
    print(df.columns)

get_medias("french.mush")



