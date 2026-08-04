# A reusable module: run one containerised web service on a Docker network.
# It declares the image, a network, and the container — OpenTofu figures out the
# order from the references between them.

resource "docker_network" "this" {
  name = "${var.name}-net"
}

resource "docker_image" "this" {
  name         = var.image
  keep_locally = var.keep_image_locally # true = use the local build, don't pull
}

resource "docker_container" "this" {
  name  = var.name
  image = docker_image.this.image_id

  networks_advanced {
    name = docker_network.this.name
  }

  ports {
    internal = var.internal_port
    external = var.external_port
  }

  # turn the env map into Docker's ["KEY=value", ...] form
  env = [for k, v in var.env : "${k}=${v}"]

  restart = "unless-stopped"

  healthcheck {
    test     = ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:${var.internal_port}/health').status==200 else 1)"]
    interval = "30s"
    timeout  = "3s"
    retries  = 3
  }
}
