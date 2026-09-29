from instagrapi import Client
import pandas as pd
import numpy as np
import json
import os
from dotenv import load_dotenv, dotenv_values 
import requests
import time
import datetime
from google.cloud import storage
import random

#Authentification 

load_dotenv()

PROJECT_ID = 'performance-analyzer-1309'

#Get secrets
def get_secret(name):
    if name in os.environ:
        return os.environ[name]

    from google.cloud import secretmanager

    client = secretmanager.SecretManagerServiceClient()
    path = f"projects/{PROJECT_ID}/secrets/{name}/versions/latest"
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
    cl.set_proxy(proxy)
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
    user = cl.user_info_by_username_v1(user)

    #Get medias from user and stores it into a dataFrame
    time.sleep(random.uniform(5,15))
    medias = cl.user_medias_v1(user.pk,amount=0)
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
    frames = []
    for acc in accounts:
        frames.append(get_medias(acc))
        time.sleep(random.uniform(60, 90))
    df = pd.concat(frames, axis=0, ignore_index=True)
    return df.copy()

lst = ["french.mush","french.mush.it","bonjourdrink","miumlab_fr",]


df = merge_df(lst)

def upload_parquet_togcloud(df,filename,project,bucket):
    #convert the df to parquet
    parquet_file = df.to_parquet(index=False)

    #Initialize GCS client
    client = storage.Client(project=project)
    bucket = client.bucket(bucket)
    bucket.blob(filename).upload_from_string(parquet_file,content_type="application/octet-stream")


today_date = datetime.date.today().isoformat()

filename = f"dataset/date={today_date}/data.parquet"

upload_parquet_togcloud(df,filename,"performance-analyzer-1309","insta-perf-analyzer-bucket")




