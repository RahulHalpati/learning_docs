variable "name" {
  type        = string
  description = "Container name."
}

variable "image" {
  type        = string
  description = "Image reference (e.g. linkstash:local)."
}

variable "internal_port" {
  type        = number
  default     = 8000
  description = "Port the app listens on inside the container."
}

variable "external_port" {
  type        = number
  description = "Host port to publish the app on."

  validation {
    condition     = var.external_port > 1024 && var.external_port < 65536
    error_message = "external_port must be an unprivileged port (1025-65535)."
  }
}

variable "env" {
  type        = map(string)
  default     = {}
  description = "Environment variables for the container."
}

variable "keep_image_locally" {
  type        = bool
  default     = true
  description = "Use a locally-built image instead of pulling from a registry."
}
