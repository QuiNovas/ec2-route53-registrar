=====================
ec2-route53-registrar
=====================

.. _APL2: http://www.apache.org/licenses/LICENSE-2.0.txt
.. _EC2 Instance State-change Notification: https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/EventTypes.html#ec2_event_type

Registers/deregisters A records in Route53 based upon Cloudwatch EC2 events.
This function is expecting AWS Cloudwatch
`EC2 Instance State-change Notification`_ events. It will register an instance
with Route53 when the status of that event is ``running`` and deregister it
from Route53 when the status is ``shutting-down``, ``stopped``, ``stopping``,
or ``terminated``.

Required AWS Resources
----------------------
- EC2
- Route53

Required Permissions
--------------------
- AmazonEC2ReadOnlyAccess (AWS Managed Policy)
- route53:GetHostedZone
- route53:ChangeResourceRecordSets

Environment Variables
---------------------
**DNS_NAME_PREFIX** Optional
  The prefix to put before the name. For example, if the
  instance's public DNS is ``ec2-3-81-42-180.compute-1.amazonaws.com``
  , the zone is ``foo.bar.com`` and the prefix is ``my-prefix-``, then
  the resulting FQDN would be ``my-prefix-ec2-3-81-42-180.foo.bar.com``.
  Defaults to the empty string.

**DNS_NAME_SUFFIX** Optional
  The suffix to put after the name. For example, if the
  instance's public DNS is ``ec2-3-81-42-180.compute-1.amazonaws.com``
  , the zone is ``foo.bar.com`` and the suffix is ``-my-suffix``, then
  the resulting FQDN would be ``ec2-3-81-42-180-my-suffix.foo.bar.com``.
  Defaults to the empty string.

**DNS_TTL** Optional
  The TTL on the created DNS records. Defaults to ``300``.

**EC2_INSTANCE_TAGS** Optional
  A map of key/value pairs for tags to match. The
  value is treated as a regular expression for matching
  purposes. In minified (no white space) JSON format. Default is
  ``{}``.

**HOSTED_ZONE_ID** Required
  The Route53 Hosted Zone ID for the zone to Registers
  ec2 instance records in.

**MULTI_VALUE_ANSWER** Optional
  If ``false``, the new label will be
  ``DNS_NAME_PREFIX`` + ``ec2-dns-label`` + ``DNS_NAME_SUFFIX``.
  If ``true``, the new label will be
  ``DNS_NAME_PREFIX`` + ``DNS_NAME_SUFFIX``. Defaults to ``false``


License: `APL2`_
