resource "aws_iam_role_policy" "s3_iam_role_policy" {
  name_prefix = "assetstore-"
  role = "${var.role_id}"

  # TODO this allows all actions, ideally this would only be limited to what Girder
  # actually needs. This means removing things such as create/delete bucket permissions.
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:*"],
      "Resource": ["${aws_s3_bucket.assetstore.arn}", "${aws_s3_bucket.assetstore.arn}/*"]
    }
  ]
}
EOF
}

resource "aws_s3_bucket" "assetstore" {
  bucket_prefix = "assetstore-"
  force_destroy = "${var.s3_force_destroy}"

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "POST", "GET", "DELETE"]
    allowed_origins = "${var.s3_cors_allowed_origins}"
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}
