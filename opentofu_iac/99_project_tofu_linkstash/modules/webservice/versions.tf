# A child module must declare the SOURCE of any provider whose name isn't the
# default `hashicorp/<name>`. Without this, OpenTofu assumes `hashicorp/docker`
# (which doesn't exist) and `init` fails. This block only names the source; the
# provider is *configured* in the root module.
terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}
