output "route53_nameservers" {
  description = "Set THESE as the nameservers for your domain at GoDaddy (step 5 in the runbook)."
  value       = aws_route53_zone.main.name_servers
}

output "cloudfront_domain" {
  description = "The CloudFront distribution domain (for debugging)."
  value       = aws_cloudfront_distribution.site.domain_name
}

output "site_url" {
  value = "https://${var.domain_name}"
}
