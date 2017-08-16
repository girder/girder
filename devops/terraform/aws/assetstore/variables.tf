variable "role_id" {
  description = "The id of the IAM role to attach the assetstore policy to."
}

variable "s3_cors_allowed_origins" {
  default = ["*"]  # TODO only allow from deployed url
  description = "List of allowed origins for CORs rule on S3 bucket."
}

variable "s3_force_destroy" {
  default = false
  description = "Whether or not to forcibly destroy S3 buckets (whether they have data in them or not)."
}
