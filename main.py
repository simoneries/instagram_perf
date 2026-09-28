from instagrapi import Client
import pandas as pd
import numpy as np
import json
import os
from dotenv import load_dotenv, dotenv_values 
import requests
import time
import datetime

#Authentification 

load_dotenv()

#Get secrets
def get_secret(name):
    if name in os.environ:
        return os.environ[name]

    from google.cloud import secretmanager

    client = secretmanager.SecretManagerServiceClient()
    path = f"projects/{os.environ['performance-analyzer-1309']}/secrets/{name}/versions/latest"
    return client.access_secret_version(name=path).payload.data.decode('UTF-8')




ENV_PROXY_ADRESS = get_secret("PROXY_ADRESS")
ENV_PROXY_PORT = get_secret("PROXY_PORT")
ENV_PROXY_USERNAME = get_secret("PROXY_USERNAME")
ENV_PROXY_PASSWORD = get_secret("PROXY_PASSWORD")

ENV_IG_USERNAME = get_secret("IG_USERNAME")
ENV_IG_PASSWORD = get_secret("IG_PASSWORD")


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
    medias = cl.user_medias(user.pk,amount=10)
    rows = [media.model_dump(mode = "json") for media in medias]
    df = pd.json_normalize(rows,sep="_") 

    #crée une colonne de coauteurs
    df["coauthors"] = df["coauthor_producers"].apply(lambda liste: [d['username'] for d in liste])
    df["coauthors_pk"] = df["coauthor_producers"].apply(lambda liste: [d['pk'] for d in liste])

    #crée une colonne de sponsors
    df["sponsors"] = df["sponsor_tags"].apply(lambda liste: [d['username'] for d in liste])
    df["sponsors_pk"] = df["sponsor_tags"].apply(lambda liste: [d['pk'] for d in liste])

    #crée une colonne pour marquer la date de collecte
    time_now = datetime.datetime.now()
    df["scraping_time"] = time_now



    return df

def merge_df(accounts):
    df = pd.DataFrame()
    frames = [get_medias(acc) for acc in accounts]
    df = pd.concat(frames,axis=0,ignore_index=True)
    return df.copy()

lst = ["french.mush","french.mush.it","bonjourdrink","bulk","miumlab_fr","nutrimea_fr","foursigmatic","ryzesuperfoods"]

df = merge_df(lst)

df.to_csv("test.csv")



