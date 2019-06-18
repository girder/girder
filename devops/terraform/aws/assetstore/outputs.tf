output "s3_bucket" {
  value = "${aws_s3_bucket.assetstore.id}"
}

output "iam_role_policy_id" {
  value = "${aws_iam_role_policy.s3_iam_role_policy.id}"
}
