import click
import boto3
import uuid

def get_client(service, profile, region):
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client(service)

@click.group()
@click.option("--profile", required=True, help="AWS profile to use")
@click.option("--region", default="us-east-1", help="AWS region")
@click.option("--owner", required=True, help="Owner tag for filtering resources")
@click.pass_context
def cli(ctx, profile, region, owner):
    ctx.ensure_object(dict)
    ctx.obj["profile"] = profile
    ctx.obj["region"] = region
    ctx.obj["owner"] = owner

@cli.group()
@click.pass_context
def ec2(ctx):
    pass

@ec2.command()
@click.pass_context
def list(ctx):
    ec2 = get_client("ec2", ctx.obj["profile"], ctx.obj["region"])
    resp = ec2.describe_instances(
        Filters=[{"Name": "tag:Owner", "Values": [ctx.obj["owner"]]}]
    )
    for r in resp["Reservations"]:
        for inst in r["Instances"]:
            state = inst["State"]["Name"]
            inst_type = inst["InstanceType"]
            inst_id = inst["InstanceId"]
            ip = inst.get("PublicIpAddress", "N/A")
            print(f"{inst_id} {state} {inst_type} {ip}")

@ec2.command()
@click.option("--type", default="t3.micro", help="Instance type")
@click.option("--os", default="amazon-linux", help="OS type")
@click.pass_context
def create(ctx, type, os):
    ec2 = get_client("ec2", ctx.obj["profile"], ctx.obj["region"])
    ssm = get_client("ssm", ctx.obj["profile"], ctx.obj["region"])
    ami_params = {
         "amazon-linux": "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64",
        "ubuntu": "/aws/service/canonical/ubuntu/server/20.04/stable/current/amd64/hvm/ebs-gp2/ami-id",
    }

    param_name = ami_params[os]
    ami = ssm.get_parameter(Name=param_name)["Parameter"]["Value"]

    resp = ec2.run_instances(
        ImageId=ami,
        InstanceType=type,
        MinCount=1,
        MaxCount=1,
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "Owner", "Value": ctx.obj["owner"]},
                    {"Key": "CreatedBy", "Value": "platform-cli"},
                ],
            }
        ],
    )
    inst_id = resp["Instances"][0]["InstanceId"]
    print(f"Created {inst_id}")

@ec2.command()
@click.argument("instance_id")
@click.pass_context
def stop(ctx, instance_id):
    ec2 = get_client("ec2", ctx.obj["profile"], ctx.obj["region"])
    ec2.stop_instances(InstanceIds=[instance_id])
    print(f"Stopped {instance_id}")

@ec2.command()
@click.argument("instance_id")
@click.pass_context
def start(ctx, instance_id):
    ec2 = get_client("ec2", ctx.obj["profile"], ctx.obj["region"])
    ec2.start_instances(InstanceIds=[instance_id])
    print(f"Started {instance_id}")

@ec2.command()
@click.argument("instance_id")
@click.pass_context
def terminate(ctx, instance_id):
    ec2 = get_client("ec2", ctx.obj["profile"], ctx.obj["region"])
    ec2.terminate_instances(InstanceIds=[instance_id])
    print(f"Terminated {instance_id}")

@cli.group()
@click.pass_context
def s3(ctx):
    pass

@s3.command()
@click.option("--name", required=True, help="Bucket name")
@click.pass_context
def create(ctx, name):
    s3 = get_client("s3", ctx.obj["profile"], ctx.obj["region"])
    bucket_name = f"{name}-{uuid.uuid4().hex[:8]}"
    s3.create_bucket(Bucket=bucket_name)
    s3.put_bucket_tagging(
        Bucket=bucket_name,
        Tagging={
            "TagSet": [
                {"Key": "Owner", "Value": ctx.obj["owner"]},
                {"Key": "CreatedBy", "Value": "platform-cli"},
            ]
        },
    )
    print(f"bucket created: {bucket_name}")

@s3.command()
@click.pass_context
def list(ctx):
    s3 = get_client("s3", ctx.obj["profile"], ctx.obj["region"])
    resp = s3.list_buckets()
    for b in resp["Buckets"]:
        print(b["Name"])

@s3.command()
@click.option("--name", required=True, help="Bucket name")
@click.option("--file", required=True, help="File to upload")
@click.pass_context
def upload(ctx, name, file):
    s3 = get_client("s3", ctx.obj["profile"], ctx.obj["region"])
    key = file.split("/")[-1]
    s3.upload_file(file, name, key)
    print(f"uploaded {file} to {name}")

@cli.group()
@click.pass_context
def route53(ctx):
    pass

@route53.command()
@click.option("--name", required=True, help="Domain name (e.g. example.com)")
@click.pass_context
def create_zone(ctx, name):
    r53 = get_client("route53", ctx.obj["profile"], ctx.obj["region"])
    resp = r53.create_hosted_zone(
        Name=name,
        CallerReference=str(uuid.uuid4()),
        HostedZoneConfig={
            "Comment": f"Zone for {ctx.obj['owner']}",
            "PrivateZone": False,
        },
    )
    zid = resp["HostedZone"]["Id"].split("/")[-1]
    print(f"{name} {zid}")

@route53.command()
@click.pass_context
def list(ctx):
    r53 = get_client("route53", ctx.obj["profile"], ctx.obj["region"])
    resp = r53.list_hosted_zones()
    for z in resp["HostedZones"]:
        print(f"{z['Name']} {z['Id'].split('/')[-1]}")

@route53.command()
@click.option("--zone", required=True, help="Domain name")
@click.option("--action", required=True, type=click.Choice(["create", "delete", "update"]))
@click.option("--type", required=True, help="Record type (A, CNAME, etc.)")
@click.option("--name", required=True, help="Record name (e.g. test.example.com)")
@click.option("--value", help="Record value (for create/update)")
@click.pass_context
def record(ctx, zone, action, type, name, value):
    r53 = get_client("route53", ctx.obj["profile"], ctx.obj["region"])
    zones = r53.list_hosted_zones_by_name(DNSName=zone)["HostedZones"]
    if not zones:
        print("Zone not found")
        return
    zid = zones[0]["Id"].split("/")[-1]

    rr = {
        "Name": name,
        "Type": type,
    }
    if action in ["create", "delete", "update"]:
        rr["TTL"] = 300
        rr["ResourceRecords"] = [{"Value": value}]

    if action.lower() == "update":
        action = "UPSERT"
    else:
        action = action.upper()

    r53.change_resource_record_sets(
        HostedZoneId=zid,
        ChangeBatch={"Changes": [{"Action": action.upper(), "ResourceRecordSet": rr}]},
    )
    print(f"record {action.upper()} {type} {name} -> {value if value else ''}")

if __name__ == "__main__":
    cli()
