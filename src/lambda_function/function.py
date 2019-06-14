import boto3
import json
import logging.config
import re

from os import environ


DNS_NAME_PREFIX = environ.get('DNS_NAME_PREFIX', '')
DNS_NAME_SUFFIX = environ.get('DNS_NAME_SUFFIX', '')
DNS_TTL = int(environ.get('DNS_TTL', '300'))
EC2_INSTANCE_TAGS = json.loads(environ.get('EC2_INSTANCE_TAGS', '{}'))
HOSTED_ZONE_ID = environ['HOSTED_ZONE_ID']
MULTI_VALUE_ANSWER = environ.get('MULTI_VALUE_ANSWER', 'false') == 'true'


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
        if not MULTI_VALUE_ANSWER:
          record_change = {
            'Action': 'UPSERT' if state == 'running' else 'DELETE',
            'ResourceRecordSet': {
              'Name': record_name,
              'Type': 'A',
              'TTL': DNS_TTL,
              'ResourceRecords': [
                {
                  'Value': instance.private_ip_address if private_zone else instance.public_ip_address
                }
              ]
            }
          }
        else:
          record_change = {
            'Action': 'UPSERT' if state == 'running' else 'DELETE',
            'ResourceRecordSet': {
              'Name': record_name,
              'Type': 'A',
              'SetIdentifier': instance.id,
              'MultiValueAnswer': True,
              'TTL': DNS_TTL,
              'ResourceRecords': [
                {
                  'Value': instance.private_ip_address if private_zone else instance.public_ip_address
                }
              ]
            }
          }
        try:
          ROUTE53.change_resource_record_sets(
            HostedZoneId=HOSTED_ZONE_ID,
            ChangeBatch={
              'Changes': [
                record_change
              ]
            }
          )
        except ROUTE53.exceptions.InvalidChangeBatch as icb:
          if state == 'running':
            raise icb
        logger.info('{} DNS entry {} for instance {}'.format('Upserted' if state == 'running' else 'Deleted', record_name, instance.id))
      else:
        logger.info('Tags {} do not match'.format(instance.tags))
  else:
    logger.warn('Event is not an EC2 Instance State-change Notification')
  return event


def _do_tags_match(instance):
  tags = {}
  for tag in instance.tags:
    tags[tag['Key']] = tag['Value']
  for key, value in EC2_INSTANCE_TAGS.items():
    if key not in tags or not re.fullmatch(value, tags[key]):
      return False
  return True


def _get_hosted_zone_name_and_type():
  global HOSTED_ZONE_TUPLE
  if not HOSTED_ZONE_TUPLE:
    response = ROUTE53.get_hosted_zone(
      Id=HOSTED_ZONE_ID
    )
    HOSTED_ZONE_TUPLE = (response['HostedZone']['Name'], response['HostedZone']['Config']['PrivateZone'])
  return HOSTED_ZONE_TUPLE
