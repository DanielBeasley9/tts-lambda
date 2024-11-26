import boto3
import json
import uuid
import os
from botocore.exceptions import ClientError

polly_client = boto3.client('polly')
s3_client = boto3.client('s3')

S3_BUCKET = os.environ.get('S3_BUCKET')
S3_REGION = os.environ.get('AWS_REGION')
PRESIGNED_URL_EXPIRATION = 3600  # 1 hour

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        text = body.get('text', 'Hello, this is a default text!')
        voice_id = body.get('voice_id', 'Joanna')
        output_format = body.get('output_format', 'mp3')
        
        file_name = f"speech/{uuid.uuid4()}.{output_format}"
        
        response = polly_client.synthesize_speech(
            Text=text,
            VoiceId=voice_id,
            OutputFormat=output_format
        )

        if 'AudioStream' in response:
            audio_stream = response['AudioStream'].read()
            
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=file_name,
                Body=audio_stream,
                ContentType=f'audio/{output_format}'
                # No ACL='public-read' needed
            )
            try:
                presigned_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': S3_BUCKET, 'Key': file_name},
                    ExpiresIn=PRESIGNED_URL_EXPIRATION
                )
            except ClientError as e:
                print(e)
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Failed to generate pre-signed URL'})
                }
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'audio_url': presigned_url,
                    'message': 'Audio successfully saved to S3'
                })
            }
        else:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Failed to generate audio stream from Polly.'})
            }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }