# Norra — AWS deploy runbook (Phase 1: website + domain)

Goal: get **norrahq.com** live on your own AWS using Terraform. You run the steps;
the Terraform in `aws/` does the heavy lifting. Region: **ca-central-1** (Canada).

---

## 0. Install the tools (one time)
- **Terraform** ≥ 1.5 — https://developer.hashicorp.com/terraform/install
- **AWS CLI v2** — https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
- **Git** — https://git-scm.com/downloads

---

## 1. Create your AWS account
1. Go to https://aws.amazon.com → **Create an AWS Account**. Use a real email (you can use a `+aws` alias) and add a credit card.
2. **Secure the root user:** sign in as root → IAM → enable **MFA** on the root account. Don't use root for daily work.
3. **Set a budget alert** so there are no surprises: Billing → Budgets → create a **$10/month** budget with an email alert.
4. **Create an admin IAM user:**
   - IAM → Users → Create user → name `norra-admin`.
   - Attach policy **AdministratorAccess** (fine for now; tighten later).
   - Create an **access key** (CLI use case) → copy the Access Key ID + Secret.
5. **Configure the CLI:**
   ```bash
   aws configure --profile norra
   # paste the Access Key ID + Secret, region: ca-central-1, output: json
   export AWS_PROFILE=norra
   ```

---

## 2. Initialize Terraform
From the `aws/` folder (the site file is read from `../Norra-Website.html`):
```bash
cd aws
terraform init
```

## 3. Create the DNS zone first (to get your nameservers)
ACM can't validate the certificate until your domain points at Route 53, so create
the hosted zone first:
```bash
terraform apply -target=aws_route53_zone.main
terraform output route53_nameservers
```
Copy the 4 nameservers it prints.

## 4. Point GoDaddy at Route 53
In GoDaddy → your domain **norrahq.com** → **Nameservers** → **Change** → **Enter my own nameservers** → paste the 4 from step 3 → save. (Propagation is usually minutes, occasionally longer.)

## 5. Deploy everything
Once the nameservers are updated:
```bash
terraform apply
```
This creates the ACM cert (auto-validates via DNS), the S3 bucket, CloudFront, the
DNS records, and uploads `Norra-Website.html` as `index.html`.

## 6. You're live
Open **https://norrahq.com**. (CloudFront can take ~10–15 min to fully deploy the first time.)

---

## Updating the site later
Edit `Norra-Website.html`, then:
```bash
cd aws
terraform apply                      # re-uploads (etag changed)
aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"
```
(Get `<ID>` from `terraform output cloudfront_domain` / the CloudFront console.)

## Cost
S3 + CloudFront + Route 53 at low traffic ≈ **$1–2/month** (Route 53 hosted zone is $0.50/mo). The budget alert in step 1.3 protects you.

## Production note — remote Terraform state
For solo MVP, local state (`terraform.tfstate`) is fine — but it's gitignored and you
should back it up. For a team / production, switch to an **S3 backend + DynamoDB lock**
(I can add that when we set up the Lambdas in Phase 2).

---

# Source control

The repo is initialized for you. To publish it:

1. Create a **private** repo on GitHub (e.g. `norra`). Don't initialize it with a README.
2. Add the remote and push:
   ```bash
   git remote add origin https://github.com/<you>/norra.git
   git branch -M main
   git push -u origin main
   ```

**Never commit:** `*.tfstate` (it can contain secrets), `.env`, API keys, or `node_modules`
— the `.gitignore` already blocks these.

**Later (CI/CD):** a GitHub Actions workflow can run `terraform apply` and deploy the
Lambdas automatically on every push to `main`. We'll add that in Phase 2.
