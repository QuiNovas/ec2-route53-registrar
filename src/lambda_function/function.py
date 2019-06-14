import boto3
import json
import logging.config
import re

from distutils.util import strtobool
from os import environ


DNS_NAME_PREFIX = environ.get('DNS_NAME_PREFIX', '')
DNS_NAME_SUFFIX = environ.get('DNS_NAME_SUFFIX', '')
DNS_TTL = int(environ.get('DNS_TTL', '300'))
EC2_INSTANCE_TAGS = json.loads(environ.get('EC2_INSTANCE_TAGS', '{}'))
HOSTED_ZONE_ID = environ['HOSTED_ZONE_ID']
MULTI_VALUE_ANSWER = bool(stringtobool(environ.get('MULTI_VALUE_ANSWER', 'false')))


ROUTE53 = boto3.client('route53')
EC2 = boto3.resource('ec2')

HOSTED_ZONE_TUPLE = None

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
  logger.info('Processing event {}'.format(json.dumps(event)))
  if 'source' in event \
    and event['source'] == 'aws.ec2' \
      and 'detail-type' in event \
        and event['detail-type'] == 'EC2 Instance State-change Notification':
    state = event['detail']['state']
    if state != 'pending':
      instance = EC2.Instance(event['detail']['instance-id'])
      if _do_tags_match(instance):
        zone_name, private_zone = _get_hosted_zone_name_and_type()
        source_fqdn = instance.private_dns_name if private_zone else instance.public_dns_name
        record_name = '{}{}.{}'.format(DNS_NAME_PREFIX, DNS_NAME_SUFFIX, zone_name) \
          if MULTI_VALUE_ANSWER \
            else '{}{}{}.{}'.format(DNS_NAME_PREFIX, source_fqdn[0 : source_fqdn.index('.')], DNS_NAME_SUFFIX, zone_name)
        ROUTE53.change_resource_record_sets(
          HostedZoneId=HOSTED_ZONE_ID,
          ChangeBatch={
            'Changes': [
              'Action': 'UPSERT' if state == 'running' else 'DELETE',
              'ResourceRecordSet': {
                'Name': record_name,
                'Type': 'A',
                'MultiValueAnswer': MULTI_VALUE_ANSWER,
                'TTL': DNS_TTL,
                'ResourceRecords': [
                  {
                    'Value': instance.private_ip_address if private_zone else instance.public_ip_address
                  }
                ]
              }
            ]
          }
        )
      else:
        logger.info('Tags {} do not match'.format(instance.tags))
  else:
    logger.warn('Event is not an EC2 Instance State-change Notification')
  return event


def _do_tags_match(instance):
  tags = {}
  for tag in instance['tags']:
    tags[tag['Key']] = tag['Value']
  for key, value in EC2_INSTANCE_TAGS:
    if key not in tags or not re.fullmatch(value, tags[key]):
      return False
  return True


def _get_hosted_zone_name_and_type():
  if not HOSTED_ZONE_TUPLE:
    response = ROUTE53.get_hosted_zone(
      ID=HOSTED_ZONE_ID
    )
    HOSTED_ZONE_TUPLE = (response['HostedZone']['Name'], response['HostedZone']['Config']['PrivateZone'])
  return HOSTED_ZONE_TUPLE
