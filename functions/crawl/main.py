# Configuration to pack python dependencies in Lambda function
import os
import sys

parent_dir = os.path.abspath(os.path.dirname(__file__))
vendor_dir = os.path.join(parent_dir, 'libs')
sys.path.append(vendor_dir)


# Main codes
from datetime import datetime
import json

import boto3
from botocore.vendored import requests
from google.cloud import automl_v1beta1 as automl

dynamodb = boto3.client('dynamodb')
predictor = automl.PredictionServiceClient()


def _get_user_timeline(user_id, since_id):
    """
    Documentation: https://developer.twitter.com/en/docs/tweets/timelines/api-reference/get-statuses-user_timeline.html
    """
    url = 'https://api.twitter.com/1.1/statuses/user_timeline.json'
    params = {
        'user_id': user_id,
        'count': 40,
        'include_rts': 'false',
    }
    if since_id:
        params['since_id'] = since_id

    headers = {
        'Authorization': f"Bearer {os.environ['TWITTER_ACCESS_TOKEN']}",
    }
    res = requests.get(url, params=params, headers=headers)
    if res.status_code != 200:
        print(f"Failed to load timeline ({res.status_code}).")
        exit(1)
    
    return res.json()


def _predict_image(path):
    """
    Documentation: https://googleapis.github.io/google-cloud-python/latest/automl/gapic/v1beta1/api.html
    """
    with open(path, 'rb') as f:
        image = f.read()

    name = f"projects/{os.environ['GCP_PROJECT_ID']}/locations/us-central1/models/{os.environ['GCP_AUTOML_MODEL_ID']}"
    payload = {'image': {'image_bytes': image}}

    return predictor.predict(name, payload).payload[0].display_name


def handle(event, context):
    """
    Environment Variables:
      - GOOGLE_APPLICATION_CREDENTIALS
      - GCP_PROJECT_ID
      - GCP_AUTOML_MODEL_ID
      - TWITTER_ACCESS_TOKEN
    """

    for user_id in map(lambda r: json.loads(r['body'])['user_id'], event['Records']):
        # Get ID of lastest tweet.
        item = dynamodb.get_item(TableName='NDSCursor', Key={'UserID': {'N': user_id}})
        if 'Item' in item:
            since_id = item['Item']['TweetID']['N']
            max_tweet_id = int(item['Item']['TweetID']['N'])
        else:
            since_id = None
            max_tweet_id = -1

        # Process tweets
        tweets = _get_user_timeline(user_id, since_id)
        for tweet in tweets:
            if tweet['id'] > max_tweet_id:
                max_tweet_id = tweet['id']
            if 'media' not in tweet['entities']:
                continue
            
            for media in tweet['entities']['media']:
                if media['type'] != 'photo':
                    continue

                media_id = media['id_str']
                media_url = media['media_url_https']

                # If the image has processed already, skip it.
                item = dynamodb.get_item(TableName='NDSMedia', Key={'MediaID': {'N': media_id}})
                if 'Item' in item:
                    print(f"Skipping {media_id}, which is already exists.")
                    continue

                # Download image.
                res_img = requests.get(media_url, stream=True)
                if res_img.status_code != 200:
                    print(f"Failed to download img {res_img.status_code}: {media_url}")
                    continue
                with open(f"/tmp/{media_id}", 'wb') as f:
                    for chuck in res_img:
                        f.write(chuck)

                # Predict image and save.
                prediction = _predict_image(f"/tmp/{media_id}")
                timestamp = int(datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y').timestamp()) * 1000
                dynamodb.put_item(TableName='NDSMedia', Item={
                    'MediaID': {'N': media_id},
                    'UserID': {'N': user_id},
                    'MediaURL': {'S': media_url},
                    'Prediction': {'S': prediction},
                    'Timestamp': {'N': str(timestamp)},
                })
        
        # Save tweet cursor
        dynamodb.put_item(TableName='NDSCursor', Item={
            'UserID': {'N': user_id},
            'TweetID': {'N': str(max_tweet_id)},
        })


if __name__ == '__main__':
    sample_event = {
        'Records': [
            {
                'messageId': '00000000-0000-0000-0000-000000000000',
                'receiptHandle': 'DUMMY',
                'body': '{"user_id":"183230661"}',
                'attributes': {},
                'messageAttributes': {},
                'md5OfBody': 'DUMMY',
                'eventSource': 'aws:sqs',
                'eventSourceARN': 'arn:aws:sqs:us-west-2:123456789012:DummyQueue',
                'awsRegion': 'ap-northeast-2',
            }
        ],
    }
    handle(sample_event, None)
