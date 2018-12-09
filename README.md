# Nedaship

## Prerequisites

  - python 3.6
  - apex ([install](http://apex.run))
  - terraform ([install](https://learn.hashicorp.com/terraform/getting-started/install.html))

## Development

### Setup Infra

```sh
terraform init
```

## Deployment

```sh
# Deploy lambda functions
apex deploy --dry-run
apex deploy

# Deploy infra
terraform plan
terraform apply
```
