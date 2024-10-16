from typing import Any
from googleapiclient.discovery import build
import psycopg2


def get_youtube_data(api_key: str, channel_ids: list[str]) -> list[dict[str, Any]]:
    """Получение данных о каналах и видео с помощью API YouTube"""

    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
    except Exception as e:
        raise ValueError("Проблема с API ключом: ", e)

    data = []
    for channel_id in channel_ids:
        channel_data = youtube.channels().list(part='snippet,statistics', id=channel_id).execute()

        videos_data = []
        next_page_token = None
        while True:
            response = youtube.search().list(part='id,snippet', channelId=channel_id, type='video',
                                             order='date', maxResults=50, pageToken=next_page_token).execute()
            videos_data.extend(response['items'])
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

        data.append({
            'channel': channel_data['items'][0],
            'videos': videos_data
        })

    return data


def create_database(database_name: str, params: dict) -> None:
    """Создает новую базу данных."""

    conn = psycopg2.connect(dbname='postgres', **params)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute(f"SELECT 1 FROM pg_database WHERE datname='{database_name}'")
    exists = cur.fetchone()
    if exists:
        cur.execute(f"DROP DATABASE {database_name}")

    cur.execute(f"CREATE DATABASE {database_name}")

    cur.close()
    conn.close()

    conn = psycopg2.connect(dbname=database_name, **params)

    with conn.cursor() as cur:
        cur.execute("""
                CREATE TABLE channels (
                    channel_id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    views INTEGER,
                    subscribers INTEGER,
                    videos INTEGER,
                    channel_url TEXT
                )
            """)

    with conn.cursor() as cur:
        cur.execute("""
                CREATE TABLE videos (
                    video_id SERIAL PRIMARY KEY,
                    channel_id INT REFERENCES channels(channel_id),
                    title VARCHAR NOT NULL,
                    publish_date DATE,
                    video_url TEXT
                )
            """)

    conn.commit()
    conn.close()


def save_data_to_database(data: list[dict[str, Any]], database_name: str, params: dict) -> None:
    """Сохранение данных в базу данных"""

    conn = psycopg2.connect(dbname=database_name, **params)

    with conn.cursor() as cur:
        for channel in data:
            channel_data = channel['channel']['snippet']
            channel_stats = channel['channel']['statistics']
            cur.execute(
                """
                INSERT INTO channels (title, views, subscribers, videos, channel_url)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING channel_id
                """,
                (channel_data['title'], int(channel_stats['viewCount']), channel_stats['subscriberCount'],
                 channel_stats['videoCount'], f"https://www.youtube.com/channel/{channel['channel']['id']}")
            )
            channel_id = cur.fetchone()[0]
            videos_data = channel['videos']
            for video in videos_data:
                video_data = video['snippet']
                cur.execute(
                    """
                    INSERT INTO videos (channel_id, title, publish_date, video_url)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (channel_id, video_data['title'], video_data['publishedAt'],
                     f"https://www.youtube.com/watch?v={video['id']['videoId']}")
                )

    conn.commit()
    conn.close()
