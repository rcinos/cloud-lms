# outputs.tf
# This file defines the output values from the Azure infrastructure Terraform configuration.
# These outputs can be used to easily retrieve important information about the deployed resources,
# such as connection strings, public IPs, or cluster details.

output "resource_group_name" {
  description = "The name of the resource group created."
  value       = azurerm_resource_group.olms_rg.name
}

output "aks_cluster_name" {
  description = "The name of the deployed AKS cluster."
  value       = azurerm_kubernetes_cluster.olms_aks.name
}

output "aks_kube_config" {
  description = "The KubeConfig for connecting to the AKS cluster."
  value       = azurerm_kubernetes_cluster.olms_aks.kube_config_raw
  sensitive   = true # Mark as sensitive as it contains credentials
}

output "course_db_hostname" {
  description = "The fully qualified domain name (FQDN) of the Course Service PostgreSQL database."
  value       = azurerm_postgresql_flexible_server.course_db.fqdn
}

output "user_db_hostname" {
  description = "The fully qualified domain name (FQDN) of the User Service PostgreSQL database."
  value       = azurerm_postgresql_flexible_server.user_db.fqdn
}

output "progress_db_hostname" {
  description = "The fully qualified domain name (FQDN) of the Progress Service PostgreSQL database."
  value       = azurerm_postgresql_flexible_server.progress_db.fqdn
}

output "service_bus_namespace_name" {
  description = "The name of the Azure Service Bus Namespace."
  value       = azurerm_servicebus_namespace.olms_sb_namespace.name
}

output "service_bus_connection_string" {
  description = "The primary connection string for the Azure Service Bus Namespace (RootManageSharedAccessKey)."
  value       = azurerm_servicebus_namespace.olms_sb_namespace.default_primary_connection_string
  sensitive   = true
}

output "storage_account_name" {
  description = "The name of the Azure Storage Account."
  value       = azurerm_storage_account.olms_storage.name
}

output "storage_account_primary_access_key" {
  description = "The primary access key for the Azure Storage Account."
  value       = azurerm_storage_account.olms_storage.primary_access_key
  sensitive   = true
}

output "acr_login_server" {
  description = "The login server URL for Azure Container Registry."
  value       = azurerm_container_registry.olms_acr.login_server
}

output "app_gateway_public_ip_address" {
  description = "The public IP address of the Azure Application Gateway."
  value       = azurerm_public_ip.app_gateway_public_ip.ip_address
}
