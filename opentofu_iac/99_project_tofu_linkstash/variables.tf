variable "image" {
  type        = string
  default     = "linkstash:local"
  description = "The linkstash image to run (build it first: see README)."
}

variable "environment" {
  type        = string
  default     = "staging"
  description = "Logical environment name; used in resource names."

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be 'staging' or 'production'."
  }
}

variable "external_port" {
  type        = number
  default     = 8088
  description = "Host port to publish linkstash on."
}
