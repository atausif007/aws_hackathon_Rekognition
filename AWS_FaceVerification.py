import boto3
import cv2

#### Creating collection Id #####

def create_collection(collection_id):
    client = boto3.client('rekognition')

    print('Creating collection:' + collection_id)
    response = client.create_collection(CollectionId=collection_id)
    print('Collection ARN: ' + response['CollectionArn'])
    print('Status code: ' + str(response['StatusCode']))
    print('Done...')

#### Comparing the images and Integratting with Dynamo DB #####

def compare_images(bucket, picture, collection_id,threshold,maxFaces):

    client = boto3.client('rekognition')
    dynamodb = boto3.resource('dynamodb')

    response = client.search_faces_by_image(CollectionId=collection_id,
                                            Image={'S3Object': {'Bucket': bucket, 'Name': picture}},
                                            FaceMatchThreshold=threshold,
                                            MaxFaces=maxFaces)

    faceMatches = response['FaceMatches']
    print('Matching faces')

    for match in faceMatches:
        print('FaceId:' + match['Face']['FaceId'])
        print('Similarity: ' + "{:.2f}".format(match['Similarity']) + "%")
        print('photo name:' + match['Face']['ExternalImageId'])
        if match['Face']['ExternalImageId'] == 'photo.jpg':
            table = dynamodb.Table('employee')
            response = table.get_item(Key={'emp_id': 12341})
            item = response['Item']
            return (item)

#### Capture the Image and uploading in S3 bucket ####

def capture_and_upload_S3(bucket, picture):

    s3 = boto3.client('s3')

    cam = cv2.VideoCapture(0)

    cv2.namedWindow("test")

    img_counter = 0

    while True:
        ret, frame = cam.read()
        if not ret:
            print("failed to grab frame")
            break
        cv2.imshow("test", frame)

        k = cv2.waitKey(1)
        if k % 256 == 27:
            # ESC pressed
            print("Escape hit, closing...")
            break
        elif k % 256 == 32:
            # SPACE pressed
            img_name = "opencv_img_{}.png".format(img_counter)
            cv2.imwrite(img_name, frame)
            s3.upload_file(img_name, bucket, picture)
            print("{} written!".format(img_name))
            img_counter += 1

    cam.release()

#### Searching for a face using an image  ####

def add_faces_to_collection(bucket, photo, collection_id):
    client = boto3.client('rekognition')
    response = client.index_faces(CollectionId=collection_id,
                                  Image={'S3Object': {'Bucket': bucket, 'Name': photo}},
                                  ExternalImageId=photo,
                                  MaxFaces=1,
                                  QualityFilter="AUTO",
                                  DetectionAttributes=['ALL'])

    print('Results for ' + photo)
    print('Faces indexed:')
    for faceRecord in response['FaceRecords']:
        print('  Face ID: ' + faceRecord['Face']['FaceId'])
        print('  Location: {}'.format(faceRecord['Face']['BoundingBox']))

    print('Faces not indexed:')
    for unindexedFace in response['UnindexedFaces']:
        print(' Location: {}'.format(unindexedFace['FaceDetail']['BoundingBox']))
        print(' Reasons:')
        for reason in unindexedFace['Reasons']:
            print('   ' + reason)
    return len(response['FaceRecords'])


def main():
    collection_id = 'Collection2'
    bucket = 'aws-project-source'
    photo = 'photo.jpg'
    picture = 'photonew.jpg'
    threshold = 70
    maxFaces = 3

    create_collection(collection_id)
    indexed_faces_count = add_faces_to_collection(bucket, photo, collection_id)
    print("Faces indexed count: " + str(indexed_faces_count))
    capture_and_upload_S3(bucket, picture)
    actualvalue = compare_images(bucket, picture, collection_id, threshold, maxFaces)

    sns_client = boto3.client('sns')

    sns_client.publish(TopicArn='arn:aws:sns:us-east-1:261523572627:employe-update', Message=str(actualvalue),
                       Subject='Matched face Information')


if __name__ == "__main__":
    main()
