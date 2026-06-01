variable "region" {
  description = "AWS region for S3 / Route 53 (Canada keeps data in-country for PHIPA)"
  type        = string
  default     = "ca-central-1"
}

variable "domain_name" {
  description = "Apex domain for the site"
  type        = string
  default     = "norrahq.com"
}

variable "site_file" {
  description = "Path (relative to this folder) of the website HTML to upload as index.html"
  type        = string
  default     = "../Norra-Website.html"
}
