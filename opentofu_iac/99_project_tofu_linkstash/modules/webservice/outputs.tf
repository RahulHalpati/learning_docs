output "container_name" {
  value       = docker_container.this.name
  description = "The running container's name."
}

output "url" {
  value       = "http://127.0.0.1:${var.external_port}"
  description = "Where the service is reachable on the host."
}

output "network" {
  value       = docker_network.this.name
  description = "The Docker network the container joined."
}
