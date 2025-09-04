import streamlit as st
import boto3
import pandas as pd
import uuid

# === Page setup ===
st.set_page_config(page_title="AWS Manager", layout="wide")
st.markdown("<h1 style='color:#4CAF50;'>🌐 Bar Katz AWS Manager</h1>", unsafe_allow_html=True)
st.write("Manage EC2, S3 and Route53 with a friendly UI.")

# AWS session (default profile)
session = boto3.Session(profile_name="default")
ec2 = session.client("ec2")
s3 = session.client("s3")
r53 = session.client("route53")

# Sidebar
st.sidebar.title("📌 Navigation")
service = st.sidebar.radio("Choose service", ["💻 EC2", "📦 S3", "🌍 Route53"])

# ================= EC2 =================
if service == "💻 EC2":
    st.markdown("<h2 style='color:#2196F3;'>💻 EC2 Instances</h2>", unsafe_allow_html=True)

    if st.button("📋 List Instances"):
        resp = ec2.describe_instances(Filters=[{"Name": "tag:Owner", "Values": ["bar"]}])
        data = []
        for r in resp["Reservations"]:
            for inst in r["Instances"]:
                name_tag = next((t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"), "")
                data.append({
                    "InstanceId": inst["InstanceId"],
                    "Name": name_tag,
                    "State": inst["State"]["Name"],
                    "Type": inst["InstanceType"]
                })
        if data:
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        else:
            st.warning("⚠️ No instances found with Owner=bar")

    st.divider()

    with st.form("create_ec2", clear_on_submit=True):
        st.subheader("🚀 Create Instance")
        instance_type = st.selectbox("Instance Type", ["t3.micro", "t3.small"])
        instance_name = st.text_input("Instance Name (optional)")
        submitted = st.form_submit_button("Create")
        if submitted:
            ami = session.client("ssm").get_parameter(
                Name="/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64"
            )["Parameter"]["Value"]
            tags = [
                {"Key": "CreatedBy", "Value": "platform-cli"},
                {"Key": "Owner", "Value": "bar"},
                {"Key": "Project", "Value": "final-exam"},
                {"Key": "Environment", "Value": "dev"}
            ]
            if instance_name:
                tags.append({"Key": "Name", "Value": instance_name})

            inst = ec2.run_instances(
                ImageId=ami,
                InstanceType=instance_type,
                MinCount=1,
                MaxCount=1,
                TagSpecifications=[{
                    "ResourceType": "instance",
                    "Tags": tags
                }]
            )
            st.success(f"✅ Created {inst['Instances'][0]['InstanceId']} ({instance_name or 'no name'})")

    st.divider()

    instance_id = st.text_input("Enter Instance ID for actions")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("▶️ Start Instance") and instance_id:
            ec2.start_instances(InstanceIds=[instance_id])
            st.info(f"Started {instance_id}")
    with col2:
        if st.button("⏸️ Stop Instance") and instance_id:
            ec2.stop_instances(InstanceIds=[instance_id])
            st.warning(f"Stopped {instance_id}")
    with col3:
        if st.button("🗑️ Terminate Instance") and instance_id:
            ec2.terminate_instances(InstanceIds=[instance_id])
            st.error(f"Terminated {instance_id}")


# ================= S3 =================
elif service == "📦 S3":
    st.markdown("<h2 style='color:#FF9800;'>📦 S3 Buckets</h2>", unsafe_allow_html=True)

    if st.button("📋 List Buckets"):
        resp = s3.list_buckets()
        names = [b["Name"] for b in resp["Buckets"]]
        if names:
            st.table(pd.DataFrame(names, columns=["Bucket Name"]))
        else:
            st.warning("⚠️ No buckets found")

    st.divider()

    with st.form("create_bucket", clear_on_submit=True):
        st.subheader("🛠️ Create Bucket")
        bucket_name = st.text_input("Bucket Name")
        submitted = st.form_submit_button("Create")
        if submitted and bucket_name:
            s3.create_bucket(Bucket=bucket_name)
            st.success(f"✅ Bucket {bucket_name} created")

    st.divider()

    uploaded_file = st.file_uploader("📤 Upload file to a bucket")
    bucket_target = st.text_input("Target bucket name")
    if uploaded_file and bucket_target:
        if st.button("Upload"):
            s3.upload_fileobj(uploaded_file, bucket_target, uploaded_file.name)
            st.success(f"✅ Uploaded {uploaded_file.name} to {bucket_target}")

# ================= Route53 =================
elif service == "🌍 Route53":
    st.markdown("<h2 style='color:#9C27B0;'>🌍 Route53 DNS</h2>", unsafe_allow_html=True)

    if st.button("📋 List Hosted Zones"):
        zones = r53.list_hosted_zones()["HostedZones"]
        if zones:
            data = [{"Name": z["Name"], "Id": z["Id"]} for z in zones]
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        else:
            st.warning("⚠️ No hosted zones available")

    st.divider()

    with st.form("create_zone", clear_on_submit=True):
        st.subheader("➕ Create Hosted Zone")
        zone_name = st.text_input("Domain Name (example: bar-exam.com)")
        submitted = st.form_submit_button("Create Zone")
        if submitted and zone_name:
            try:
                resp = r53.create_hosted_zone(
                    Name=zone_name,
                    CallerReference=str(uuid.uuid4())
                )
                st.success(f"✅ Hosted Zone created: {resp['HostedZone']['Name']} ({resp['HostedZone']['Id']})")
            except Exception as e:
                st.error(f"❌ Error creating hosted zone: {e}")

    st.divider()

    zones = r53.list_hosted_zones()["HostedZones"]
    zone_options = [z["Name"].rstrip(".") for z in zones]

    if not zone_options:
        st.warning("⚠️ No hosted zones available yet – create one above")
    else:
        with st.form("dns_record", clear_on_submit=True):
            st.subheader("📝 Manage DNS Record")

            zone_choice = st.selectbox("Select Zone", zone_options)
            action = st.selectbox("Action", ["create", "update", "delete"])
            record_type = st.selectbox("Type", ["A", "CNAME", "TXT"])
            record_name = st.text_input("Record Name (example: test.bar-exam.com)")
            record_value = st.text_input("Record Value (for create/update)")

            submitted = st.form_submit_button("Apply Change")
            if submitted and zone_choice and record_name:
                zid = None
                for z in zones:
                    if z["Name"].rstrip(".") == zone_choice.rstrip("."):
                        zid = z["Id"]
                        break

                if not zid:
                    st.error("❌ Zone not found")
                else:
                    if action == "delete":
                        records = r53.list_resource_record_sets(HostedZoneId=zid)
                        target = None
                        for rec in records["ResourceRecordSets"]:
                            if rec["Name"].rstrip(".") == record_name.rstrip(".") and rec["Type"] == record_type:
                                target = rec
                                break
                        if not target:
                            st.error("❌ Record not found")
                        else:
                            rr = {
                                "Name": target["Name"],
                                "Type": target["Type"],
                                "TTL": target["TTL"],
                                "ResourceRecords": target["ResourceRecords"]
                            }
                            act = "DELETE"
                    else:
                        rr = {
                            "Name": record_name,
                            "Type": record_type,
                            "TTL": 300,
                            "ResourceRecords": [{"Value": record_value}]
                        }
                        act = "CREATE" if action == "create" else "UPSERT"

                    r53.change_resource_record_sets(
                        HostedZoneId=zid,
                        ChangeBatch={"Changes": [{"Action": act, "ResourceRecordSet": rr}]}
                    )
                    st.success(f"✅ Record {act} {record_type} {record_name} -> {record_value or ''}")
