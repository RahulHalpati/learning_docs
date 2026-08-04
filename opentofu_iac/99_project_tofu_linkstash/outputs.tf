output "url" {
  value       = module.linkstash.url
  description = "Where linkstash is serving."
}

output "container_name" {
  value       = module.linkstash.container_name
  description = "The running container's name."
}
