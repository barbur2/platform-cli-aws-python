### 📂 Demo Evidence

This file shows proof that the CLI works as required.

## EC2

This file shows proof that the Platform CLI works as expected.
All commands were executed using the AWS profile dev with owner bar.

# ✅ Create

python cli.py --profile dev --owner bar ec2 create --type t3.micro --os amazon-linux
Created i-08e77fa8399edf0a6

# 📋 List

python cli.py --profile dev --owner bar ec2 list
i-08e77fa8399edf0a6  running  t3.micro

# ⏸ Stop

python cli.py --profile dev --owner bar ec2 stop i-08e77fa8399edf0a6
stopped i-08e77fa8399edf0a6

# ▶️ Start

python cli.py --profile dev --owner bar ec2 start i-08e77fa8399edf0a6
started i-08e77fa8399edf0a6

# 🗑 Terminate

python cli.py --profile dev --owner bar ec2 terminate i-08e77fa8399edf0a6
Terminated i-08e77fa8399edf0a6

## 📦 S3

# ✅ Create

python cli.py --profile dev --owner bar s3 create --name bar-bucket
python cli.py --profile dev --owner bar s3 create --name bar-bucket-293602529
bucket created: bar-bucket-293602529

# 📤 Upload

python cli.py --profile dev --owner bar s3 upload --name bar-bucket-293602529 --file test.txt
uploaded test.txt to bar-bucket-293602529

# 📋 List

python cli.py --profile dev --owner bar s3 list
bar-bucket-293602529

## 🌍 Route53

# ✅ Create

python cli.py --profile dev --owner bar route53 create-zone --name bar-test.com
bar-test.com Z019789317KPBDXPYXJA1

# 📋 Zone list

python cli.py --profile dev --owner bar route53 list
bar-test.com. Z019789317KPBDXPYXJA1
bar-test.com.   Z07829801P6PSA6DVD5J1

# 📝 Record create

python cli.py --profile dev --owner bar route53 record --zone bar-test.com --action create --type A --name test.bar-test.com --value 1.2.3.4
record CREATE A test.bar-test.com -> 1.2.3.4
# 🔄 Record update

python cli.py --profile dev --owner bar route53 record --zone bar-test.com --action update --type A --name test.bar-test.com --value 5.6.7.8
record UPSERT A test.yuval-test.com -> 5.6.7.8
python cli.py --profile dev --owner bar route53 record --zone bar-test.com --action create --type A --name test.bar-test.com --value 1.2.3.4
record CREATE A test.yuvalz-test.com -> 1.2.3.4
