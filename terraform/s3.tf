resource "random_id" "bucket_suffix" {
  byte_length = 3
}

resource "aws_s3_bucket" "output" {
  bucket = "${var.project_name}-outputs-${random_id.bucket_suffix.hex}"
}

resource "aws_s3_bucket_website_configuration" "output" {
  bucket = aws_s3_bucket.output.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

# Static website hosting requires the bucket to be publicly readable.
# This bucket should only ever hold build output, never secrets.
resource "aws_s3_bucket_public_access_block" "output" {
  bucket = aws_s3_bucket.output.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "output_public_read" {
  bucket = aws_s3_bucket.output.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.output.arn}/*"
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.output]
}
