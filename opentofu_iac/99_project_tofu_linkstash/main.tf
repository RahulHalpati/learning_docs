# Provision linkstash (the app from the CI/CD course) with the reusable module.
# `tofu apply` builds the real container; `tofu destroy` removes it.

module "linkstash" {
  source = "./modules/webservice"

  name          = "linkstash-${var.environment}"
  image         = var.image
  internal_port = 8000
  external_port = var.external_port

  env = {
    HOST = "0.0.0.0" # bind all interfaces so the published port is reachable
    PORT = "8000"
  }
}
