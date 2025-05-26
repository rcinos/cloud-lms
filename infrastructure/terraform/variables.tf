# variables.tf
# This file defines the input variables for the Azure infrastructure Terraform configuration.
# These variables allow you to customize the deployment without modifying the main configuration file.

variable "resource_group_name" {
  description = "The name of the Azure Resource Group where all resources will be deployed."
  type        = string
  default     = "olms-rg-dev" # A sensible default for development
}

variable "location" {
  description = "The Azure region where resources will be deployed (e.g., 'East US', 'West Europe')."
  type        = string
  default     = "East US" # Choose a region close to you or your users
}

variable "environment" {
  description = "The deployment environment (e.g., 'dev', 'test', 'prod')."
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "A short name for the project, used as a prefix for resource names."
  type        = string
  default     = "olms"
}

variable "aks_cluster_name" {
  description = "The name of the Azure Kubernetes Service (AKS) cluster."
  type        = string
  default     = "olms-aks-cluster"
}

variable "aks_node_count" {
  description = "The number of nodes in the AKS default node pool."
  type        = number
  default     = 2 # Start with 2 nodes for a basic cluster
}

variable "db_admin_username" {
  description = "The administrator username for the PostgreSQL databases."
  type        = string
  default     = "olmsadmin"
}

variable "db_admin_password" {
  description = "The administrator password for the PostgreSQL databases."
  type        = string
  sensitive   = true # Mark as sensitive to prevent logging in plain text
}

variable "service_bus_namespace_name" {
  description = "The name of the Azure Service Bus Namespace."
  type        = string
  default     = "olms-servicebus-ns"
}

variable "storage_account_name" {
  description = "The name of the Azure Storage Account (must be globally unique)."
  type        = string
  default     = "olmsstorageaccountdev" # Remember to change this for production or if it conflicts
}

variable "acr_name" {
  description = "The name of the Azure Container Registry."
  type        = string
  default     = "olmsacrdev" # Remember to change this for production or if it conflicts
}

variable "app_gateway_name" {
  description = "The name of the Azure Application Gateway."
  type        = string
  default     = "olms-app-gateway"
}
