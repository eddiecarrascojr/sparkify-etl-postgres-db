import os
import glob
import psycopg2
import pandas as pd
from sql_queries import *


def process_song_file(cur, filepath):
    """
    :param cur: cursor object from psycopg2
    :param filepath: a specified file path for json song files.
    :return: extracts, transforms, and loads json files into database.
    """
    # open song file
    df = pd.read_json(filepath, lines=True)

    for values in df.values:
        artist_id, artist_latitude, artist_location, artist_longitude, artist_name, duration, num_songs, song_id, title, year = values

        # insert song record
        song_data = [song_id, title, artist_id, year, duration]
        cur.execute(song_table_insert, song_data)

        # insert artist record
        artist_data = [artist_id, artist_name, artist_location, artist_longitude, artist_latitude]
        cur.execute(artist_table_insert, artist_data)


def process_log_file(cur, filepath):
    """
    :param cur: cursor object from psycopg2
    :param filepath: a specified file path for json user log files.
    :return: extracts, transforms, and loads json files into database.
    """
    # open log file
    df = pd.read_json(filepath, lines=True)

    # filter by NextSong action
    df = df[df['page'] == 'NextSong']

    # convert timestamp column to datetime
    time_data = pd.to_datetime(df['ts'] / 1000.0, unit='s')

    # insert time data records
    time_data = list(zip(time_data.values, time_data.dt.hour.values, time_data.dt.day.values, time_data.dt.week,
                         time_data.dt.month, time_data.dt.year, time_data.dt.weekday_name))

    column_labels = ['start_time', 'hour', 'day', 'week', 'month', 'year', 'weekday']
    time_df = pd.DataFrame(time_data, columns=column_labels)

    for i, row in time_df.iterrows():
        cur.execute(time_table_insert, list(row))

    # load user table
    user_df = df[['userId', 'firstName', 'lastName', 'gender', 'level']]

    # insert user records
    for i, row in user_df.iterrows():
        cur.execute(user_table_insert, row)

    # insert songplay records
    for index, row in df.iterrows():

        # get songid and artistid from song and artist tables
        cur.execute(song_select, (row.song, row.artist, row.length))
        results = cur.fetchone()

        # To avoid error check if there is a result, if not set to NULL
        if results:
            songid, artistid = results
        else:
            songid, artistid = None, None

        # insert songplay record
        songplay_data = (index, pd.to_datetime(row.ts / 1000.0, unit='s'), int(row.userId), row.level, songid, \
                         artistid, row.sessionId, row.location, row.userAgent)
        cur.execute(songplay_table_insert, songplay_data)


def process_data(cur, conn, filepath, func):
    """
    :param cur: cursor object from psycopg2
    :param conn: connection object from psycopg2
    :param filepath: list of file path or directories with json files.
    :param func: a specified processing function either process_log_file or process_song_file
    :return: processed json files into etl process for tables.
    """
    # get all files matching extension from directory
    all_files = []
    for root, dirs, files in os.walk(filepath):
        files = glob.glob(os.path.join(root, '*.json'))
        for f in files:
            all_files.append(os.path.abspath(f))

    # get total number of files found
    num_files = len(all_files)
    print('{} files found in {}'.format(num_files, filepath))

    # iterate over files and process
    for i, datafile in enumerate(all_files, 1):
        func(cur, datafile)
        conn.commit()
        print('{}/{} files processed.'.format(i, num_files))


def main():
    """
    :return: the order for all functions to run for json files to be properly loaded into database.
    """
    conn = psycopg2.connect("host=127.0.0.1 dbname=sparkifydb user=student password=student")
    cur = conn.cursor()

    process_data(cur, conn, filepath='data/song_data', func=process_song_file)
    process_data(cur, conn, filepath='data/log_data', func=process_log_file)

    conn.close()


if __name__ == "__main__":
    main()
