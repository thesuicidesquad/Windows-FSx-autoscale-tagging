import os
import boto3
import re

def lambda_handler(event, context):
    FSx_client = boto3.client('fsx')
    # Add tags to backup according to existing File System tags
    for fsx_list in FSx_client.describe_file_systems()['FileSystems']:
        tag_list = fsx_list['Tags']
        qualified_tags = []
        for raw_tags in tag_list:
            if re.findall("^aws:", raw_tags['Key']) == []:
                qualified_tags.append(raw_tags)

        FSx_ID = fsx_list['FileSystemId']
        backup_list = [backups['ResourceARN']for backups in FSx_client.describe_backups(Filters=[{'Name':'file-system-id','Values':[FSx_ID]}])['Backups']]
        for backup in backup_list:
            FSx_client.tag_resource(ResourceARN=backup,Tags=qualified_tags)
            print(r'Backup tag added for {}'.format(backup))
    #Add tags according to tags specified in Environment Variables
    backup_list = [backups['ResourceARN']for backups in FSx_client.describe_backups()['Backups']]
    for to_tag_backups in backup_list:
        check_tag_response = FSx_client.list_tags_for_resource(
            ResourceARN=to_tag_backups
        )
        for tags in range(1,11):
            backup_tag_key = os.environ[r'BackupTagKey{}'.format(tags)]
            backup_tag_value = os.environ[r'BackupTagValue{}'.format(tags)]
            if backup_tag_key == '':
                continue
            if backup_tag_value == '':
                continue
            if backup_tag_key in check_tag_response['Tags']:
                if check_tag_response['Tags'][backup_tag_key] != backup_tag_value:
                    change_tag_response = FSx_client.tag_resource(
                        ResourceARN=to_tag_backups,
                        Tags = [
                            {
                                'Key' : backup_tag_key,
                                'Value' : backup_tag_value
                            }
                        ]
                    )
                    print(r'Backup tag modified for {}'.format(to_tag_backups))
            else:
                add_tag_response = FSx_client.tag_resource(
                    ResourceARN=to_tag_backups,
                    Tags = [
                        {
                            'Key' : backup_tag_key,
                            'Value' : backup_tag_value
                        }
                    ]
                )
                print(r'Backup tag added for {}'.format(to_tag_backups))