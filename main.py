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

PK_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pk_cache.json")

def load_pk_cache():
    if os.path.exists(PK_CACHE_FILE):
        with open(PK_CACHE_FILE) as f:
            return json.load(f)
    return {}

pk_cache = load_pk_cache()

def get_pk(username):
    """Retourne le pk d'un compte. N'appelle Instagram qu'à la première fois."""
    if username not in pk_cache:
        time.sleep(random.uniform(1, 3))
        pk_cache[username] = cl.user_info_by_username_v1(username).pk
        with open(PK_CACHE_FILE, "w") as f:
            json.dump(pk_cache, f, indent=2)
    return pk_cache[username]


def get_medias(user):
    # Récupère les médias (le pk vient du cache)
    time.sleep(random.uniform(1, 3))
    medias = cl.user_medias_v1(get_pk(user), amount=10)
    rows = [media.model_dump(mode="json") for media in medias]
    df = pd.json_normalize(rows, sep="_")

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

def get_and_merge_df(accounts):
    frames = []
    for acc in accounts:
        frames.append(get_medias(acc))
        time.sleep(random.uniform(1, 3))
    df = pd.concat(frames, axis=0, ignore_index=True)
    return df.copy()

lst = ["french.mush","french.mush.it","bonjourdrink","miumlab_fr"]

cols = ["user_pk","user_username","user_stories","scraping_time","pk","id","video_url","video_duration",
"location_lat","location_lng","crosspost","coauthors","coauthors_pk","sponsors",
"sponsors_pk","taken_at","media_type","caption_text","is_paid_partnership",
"is_affiliate","usertags","like_count","comment_count","view_count","play_count"]

df = get_and_merge_df(lst)

#filtrer sur les bonnes colonnes
df = df[cols].copy()

#fixer les types 
def clean_df(df):
    #clean strings
    for c in ["user_pk", "pk", "id", "user_username", "video_url", "caption_text"]:
        df[c]=df[c].astype("string")

    #clean integers
    for c in ["media_type", "like_count", "comment_count", "view_count", "play_count"]:
        df[c]=pd.to_numeric(df[c], errors="coerce").astype("Int64")

    # clean booleans
    for c in ["is_paid_partnership", "is_affiliate"]:
        df[c] = df[c].astype("boolean")

    # clean dates
    for c in ["taken_at", "scraping_time"]:
        df[c] = pd.to_datetime(df[c], utc=True)

    # clean floats
    for c in ["video_duration", "location_lat", "location_lng"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")

    # clean lists
    for c in ["coauthors", "coauthors_pk", "sponsors", "sponsors_pk"]:
        df[c] = df[c].map(
            lambda v: ",".join(str(x) for x in v)
            if isinstance(v, (list, tuple)) else None
        ).astype("string")

    #clean json ans pass it to string
    for c in ["crosspost", "user_stories"]:
        df[c] = df[c].map(
            lambda v: json.dumps(v, ensure_ascii=False, default=str)
            if isinstance(v, (dict, list)) else None
        ).astype("string")

    return df


def upload_parquet_togcloud(df,filename,project,bucket):
    #convert the df to parquet
    parquet_file = df.to_parquet(index=False)

    #Initialize GCS client
    client = storage.Client(project=project)
    bucket = client.bucket(bucket)
    bucket.blob(filename).upload_from_string(parquet_file,content_type="application/octet-stream")


today_date = datetime.date.today().isoformat()

filename = f"dataset/date={today_date}/data.parquet"

upload_parquet_togcloud(clean_df(df),filename,"performance-analyzer-1309","insta-perf-analyzer-bucket")




