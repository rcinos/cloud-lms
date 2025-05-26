# main.tf
# This Terraform configuration provisions the core Azure infrastructure for the
# Online Learning Management System (OLMS) microservices.
# It includes:
# - An Azure Resource Group
# - An Azure Kubernetes Service (AKS) cluster
# - Azure Database for PostgreSQL Flexible Servers for each service
# - Azure Service Bus Namespace and Queues
# - Azure Storage Account for logs and files
# - Azure Container Registry (ACR)
# - Azure Application Gateway (for ingress/load balancing)

# Configure the Azure provider
provider "azurerm" {
  features {} # This block is required to enable the features block for the provider
}

# Define a resource group to contain all resources
resource "azurerm_resource_group" "olms_rg" {
  name     = var.resource_group_name
  location = var.location
  tags = {
    environment = var.environment
    project     = "OLMS"
  }
}

# Azure Container Registry (ACR)
resource "azurerm_container_registry" "olms_acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.olms_rg.name
  location            = azurerm_resource_group.olms_rg.location
  sku                 = "Basic" # Basic SKU is sufficient for development/testing
  admin_enabled       = true # Enable admin user for easier CI/CD integration
  tags = {
    environment = var.environment
  }
}

# Azure Kubernetes Service (AKS) Cluster
resource "azurerm_kubernetes_cluster" "olms_aks" {
  name                = var.aks_cluster_name
  location            = azurerm_resource_group.olms_rg.location
  resource_group_name = azurerm_resource_group.olms_rg.name
  dns_prefix          = "${var.aks_cluster_name}-dns"

  default_node_pool {
    name       = "default"
    node_count = var.aks_node_count
    vm_size    = "Standard_DS2_v2" # Recommended VM size for AKS nodes
  }

  identity {
    type = "SystemAssigned"
  }

  tags = {
    environment = var.environment
  }
}

# Azure Database for PostgreSQL - Course Service
resource "azurerm_postgresql_flexible_server" "course_db" {
  name                   = "${var.project_name}-course-db"
  resource_group_name    = azurerm_resource_group.olms_rg.name
  location               = azurerm_resource_group.olms_rg.location
  version                = "13" # PostgreSQL version
  sku_name               = "Standard_B1ms" # Basic SKU for development
  storage_mb             = 20480 # 20 GB storage
  backup_retention_days  = 7
  geo_redundant_backup_enabled = false
  administrator_login    = var.db_admin_username
  administrator_password = var.db_admin_password
  zone                   = "1" # Deploy to a specific availability zone
  tags = {
    service = "course"
    environment = var.environment
  }
}

# Azure Database for PostgreSQL - User Service
resource "azurerm_postgresql_flexible_server" "user_db" {
  name                   = "${var.project_name}-user-db"
  resource_group_name    = azurerm_resource_group.olms_rg.name
  location               = azurerm_resource_group.olms_rg.location
  version                = "13"
  sku_name               = "Standard_B1ms"
  storage_mb             = 20480
  backup_retention_days  = 7
  geo_redundant_backup_enabled = false
  administrator_login    = var.db_admin_username
  administrator_password = var.db_admin_password
  zone                   = "1"
  tags = {
    service = "user"
    environment = var.environment
  }
}

# Azure Database for PostgreSQL - Progress Service
resource "azurerm_postgresql_flexible_server" "progress_db" {
  name                   = "${var.project_name}-progress-db"
  resource_group_name    = azurerm_resource_group.olms_rg.name
  location               = azurerm_resource_group.olms_rg.location
  version                = "13"
  sku_name               = "Standard_B1ms"
  storage_mb             = 20480
  backup_retention_days  = 7
  geo_redundant_backup_enabled = false
  administrator_login    = var.db_admin_username
  administrator_password = var.db_admin_password
  zone                   = "1"
  tags = {
    service = "progress"
    environment = var.environment
  }
}

# Azure Service Bus Namespace
resource "azurerm_servicebus_namespace" "olms_sb_namespace" {
  name                = var.service_bus_namespace_name
  location            = azurerm_resource_group.olms_rg.location
  resource_group_name = azurerm_resource_group.olms_rg.name
  sku                 = "Standard" # Standard SKU supports queues and topics
  tags = {
    environment = var.environment
  }
}

# Azure Service Bus Queues for inter-service communication
resource "azurerm_servicebus_queue" "user_enrolled_queue" {
  name                = "user-enrolled-queue"
  namespace_id        = azurerm_servicebus_namespace.olms_sb_namespace.id
  enable_partitioning = false
  max_delivery_count  = 10
}

resource "azurerm_servicebus_queue" "progress_updated_queue" {
  name                = "progress-updated-queue"
  namespace_id        = azurerm_servicebus_namespace.olms_sb_namespace.id
  enable_partitioning = false
  max_delivery_count  = 10
}

resource "azurerm_servicebus_queue" "assessment_completed_queue" {
  name                = "assessment-completed-queue"
  namespace_id        = azurerm_servicebus_namespace.olms_sb_namespace.id
  enable_partitioning = false
  max_delivery_count  = 10
}

# Azure Storage Account for logs and files
resource "azurerm_storage_account" "olms_storage" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.olms_rg.name
  location                 = azurerm_resource_group.olms_rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS" # Locally Redundant Storage for cost efficiency in dev/test
  tags = {
    environment = var.environment
  }
}

# Azure Application Gateway (for ingress and load balancing)
resource "azurerm_public_ip" "app_gateway_public_ip" {
  name                = "${var.project_name}-app-gateway-pip"
  location            = azurerm_resource_group.olms_rg.location
  resource_group_name = azurerm_resource_group.olms_rg.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_virtual_network" "app_gateway_vnet" {
  name                = "${var.project_name}-app-gateway-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.olms_rg.location
  resource_group_name = azurerm_resource_group.olms_rg.name
}

resource "azurerm_subnet" "app_gateway_subnet" {
  name                 = "app-gateway-subnet"
  resource_group_name  = azurerm_resource_group.olms_rg.name
  virtual_network_name = azurerm_virtual_network.app_gateway_vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_application_gateway" "olms_app_gateway" {
  name                = var.app_gateway_name
  resource_group_name = azurerm_resource_group.olms_rg.name
  location            = azurerm_resource_group.olms_rg.location

  sku {
    name     = "Standard_v2" # Recommended SKU for production workloads
    tier     = "Standard_v2"
    capacity = 2 # Minimum instance count
  }

  gateway_ip_configuration {
    name      = "app-gateway-ip-config"
    subnet_id = azurerm_subnet.app_gateway_subnet.id
  }

  frontend_port {
    name = "http-port"
    port = 80
  }

  frontend_port {
    name = "https-port"
    port = 443
  }

  frontend_ip_configuration {
    name                 = "app-gateway-frontend-ip"
    public_ip_address_id = azurerm_public_ip.app_gateway_public_ip.id
  }

  http_listener {
    name                           = "http-listener"
    frontend_ip_configuration_name = "app-gateway-frontend-ip"
    frontend_port_name             = "http-port"
    protocol                       = "Http"
  }

  # This is a basic setup. For a full microservices setup, you'd define
  # backend address pools, HTTP settings, and routing rules for each service.
  # Example for a default backend pool (you'd have one per service)
  backend_address_pool {
    name = "default-backend-pool"
  }

  backend_http_settings {
    name                  = "default-http-settings"
    port                  = 80 # Assuming services listen on port 80 internally in AKS
    protocol              = "Http"
    cookie_based_affinity = "Disabled"
    request_timeout       = 60
  }

  request_routing_rule {
    name                       = "rule-http"
    rule_type                  = "Basic"
    http_listener_name         = "http-listener"
    backend_address_pool_name  = "default-backend-pool"
    backend_http_settings_name = "default-http-settings"
  }

  # For HTTPS, you would add a ssl_certificate block and another http_listener
  # with protocol "Https" and associate it with the certificate.
  # For simplicity, this example focuses on the core setup.
}

# Azure Application Insights (for monitoring and metrics)
resource "azurerm_application_insights" "olms_app_insights" {
  name                = "${var.project_name}-appinsights"
  location            = azurerm_resource_group.olms_rg.location
  resource_group_name = azurerm_resource_group.olms_rg.name
  application_type    = "Web" # Or "Other" depending on your specific needs
  retention_in_days   = 90
  daily_data_cap_in_gb = 1.0 # Set a daily data cap to control costs
  tags = {
    environment = var.environment
  }
}
